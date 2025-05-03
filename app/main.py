from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import CompositionRequest, CompositionResponse, MarketPriceRequest, MarketPriceResponse, MaterialComponent
from app.agents.composition_agent import get_material_composition
from app.agents.market_agent import get_market_prices

app = FastAPI(title="Agentic AI ProcPlan API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/v1/composition", response_model=CompositionResponse)
def composition_endpoint(req: CompositionRequest):
    components = get_material_composition(req.item)
    return CompositionResponse(item=req.item, components=components)

@app.post("/v1/marketprice", response_model=MarketPriceResponse)
def marketprice_endpoint(req: MarketPriceRequest):
    if len(req.materials) != 5:
        raise HTTPException(status_code=400, detail="Exactly 5 materials must be provided.")
    prices = get_market_prices(req.materials)
    return MarketPriceResponse(prices=prices)

@app.get("/swagger", include_in_schema=False)
def custom_swagger_ui():
    from fastapi.openapi.docs import get_swagger_ui_html
    return get_swagger_ui_html(openapi_url=app.openapi_url, title=app.title + " - Swagger UI")
