from typing import List
from app.schemas import MaterialComponent

def get_material_composition(item: str) -> List[MaterialComponent]:
    # TODO: Replace with actual LLM-based breakdown using LangChain and Ollama
    # Mocked response for demonstration
    mock_components = [
        MaterialComponent(material="Steel", percentage=40.0),
        MaterialComponent(material="Plastic", percentage=25.0),
        MaterialComponent(material="Copper", percentage=15.0),
        MaterialComponent(material="Glass", percentage=10.0),
        MaterialComponent(material="Rubber", percentage=10.0),
    ]
    return mock_components
