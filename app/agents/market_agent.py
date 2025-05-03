from typing import Dict, List

def get_market_prices(materials: List[str]) -> Dict[str, float]:
    # TODO: Replace with actual LLM-based mapping and real market data
    # Mocked prices for demonstration
    mock_prices = {
        "Steel": 800.0,
        "Plastic": 1200.0,
        "Copper": 9500.0,
        "Glass": 300.0,
        "Rubber": 2000.0,
    }
    return {mat: mock_prices.get(mat, 100.0) for mat in materials}
