from pydantic import BaseModel
from typing import List, Dict

class CompositionRequest(BaseModel):
    item: str

class MaterialComponent(BaseModel):
    material: str
    percentage: float

class CompositionResponse(BaseModel):
    item: str
    components: List[MaterialComponent]

class MarketPriceRequest(BaseModel):
    materials: List[str]

class MarketPriceResponse(BaseModel):
    prices: Dict[str, float]
