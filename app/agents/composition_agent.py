from typing import List
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from app.schemas import MaterialComponent, CompositionResponse
from app.config import settings
import json

# Initialize Ollama
llm = Ollama(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
)

# Create output parser
parser = PydanticOutputParser(pydantic_object=CompositionResponse)

# Create prompt template
template = """
You are an expert in material science and product composition analysis.
Your task is to break down the given item into its main material components and their approximate percentages.

Item: {item}

Provide a detailed breakdown of the materials and their percentages.
The total percentage should sum to 100%.

Format your response as a JSON object with the following structure:
{{
    "item": "the input item",
    "components": [
        {{"material": "material name", "percentage": percentage_value}},
        ...
    ]
}}

Example response:
{{
    "item": "Smartphone",
    "components": [
        {{"material": "Glass", "percentage": 30.0}},
        {{"material": "Aluminum", "percentage": 25.0}},
        {{"material": "Plastic", "percentage": 20.0}},
        {{"material": "Copper", "percentage": 15.0}},
        {{"material": "Other Metals", "percentage": 10.0}}
    ]
}}

{format_instructions}
"""

prompt = PromptTemplate(
    template=template,
    input_variables=["item"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

def get_material_composition(item: str) -> List[MaterialComponent]:
    try:
        # Create the chain
        chain = prompt | llm
        
        # Get the response
        response = chain.invoke({"item": item})
        
        # Try to parse the response as JSON
        try:
            # Extract JSON from the response if it's wrapped in markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Parse the JSON response
            parsed_response = json.loads(response)
            return [MaterialComponent(**comp) for comp in parsed_response["components"]]
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract components from the text
            components = []
            for line in response.split("\n"):
                if ":" in line and "%" in line:
                    try:
                        material, percentage = line.split(":")
                        material = material.strip()
                        percentage = float(percentage.strip().replace("%", ""))
                        components.append(MaterialComponent(material=material, percentage=percentage))
                    except:
                        continue
            
            if components:
                return components
            
            # If all parsing attempts fail, return a default response
            return [
                MaterialComponent(material="Unknown", percentage=100.0)
            ]
            
    except Exception as e:
        print(f"Error in get_material_composition: {str(e)}")
        # Return a default response in case of any error
        return [
            MaterialComponent(material="Error", percentage=100.0)
        ]
