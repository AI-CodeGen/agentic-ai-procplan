from typing import Dict, List
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from app.config import settings
from pydantic import BaseModel
import json

# Define the response schema
class MarketPriceMapping(BaseModel):
    prices: Dict[str, float]

# Initialize Ollama
llm = Ollama(
    base_url=settings.OLLAMA_BASE_URL,
    model=settings.OLLAMA_MODEL
)

# Create output parser
parser = PydanticOutputParser(pydantic_object=MarketPriceMapping)

# Create prompt template
template = """
You are an expert in material markets and commodity trading.
Your task is to map the given materials to their approximate current market prices in USD.

Materials: {materials}

For each material, provide a realistic current market price in USD.
Consider the following factors:
- Current market conditions
- Material purity/grade
- Standard unit prices
- Recent market trends

Format your response as a JSON object with the following structure:
{{
    "prices": {{
        "material1": price1,
        "material2": price2,
        ...
    }}
}}

Example response:
{{
    "prices": {{
        "Steel": 800.0,
        "Aluminum": 2500.0,
        "Copper": 9500.0,
        "Plastic": 1200.0,
        "Glass": 300.0
    }}
}}

{format_instructions}
"""

prompt = PromptTemplate(
    template=template,
    input_variables=["materials"],
    partial_variables={"format_instructions": parser.get_format_instructions()}
)

def get_market_prices(materials: List[str]) -> Dict[str, float]:
    try:
        # Create the chain
        chain = prompt | llm
        
        # Get the response
        response = chain.invoke({"materials": materials})
        
        # Try to parse the response as JSON
        try:
            # Extract JSON from the response if it's wrapped in markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Parse the JSON response
            parsed_response = json.loads(response)
            return parsed_response["prices"]
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract prices from the text
            prices = {}
            for line in response.split("\n"):
                if ":" in line and "$" in line:
                    try:
                        material, price = line.split(":")
                        material = material.strip()
                        price = float(price.strip().replace("$", "").replace(",", ""))
                        prices[material] = price
                    except:
                        continue
            
            if prices:
                return prices
            
            # If all parsing attempts fail, return default prices
            return {mat: 100.0 for mat in materials}
            
    except Exception as e:
        print(f"Error in get_market_prices: {str(e)}")
        # Return default prices in case of any error
        return {mat: 100.0 for mat in materials}
