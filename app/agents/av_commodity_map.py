"""
Mapping of Alpha Vantage supported commodities and their symbols.
This mapping is used by the market agent to fetch real-time prices from Alpha Vantage API.
"""

ALPHA_VANTAGE_COMMODITIES = {
    # Forex (Precious Metals)
    "XAUUSD": "Gold",
    "XAGUSD": "Silver",
    "XPTUSD": "Platinum",
    "XPDUSD": "Palladium",
    
    # Commodities
    "WTI": "Crude Oil (WTI)",
    "BRENT": "Crude Oil (Brent)",
    "NATURAL_GAS": "Natural Gas",
    "COPPER": "Copper",
    "ALUMINUM": "Aluminum",
    "WHEAT": "Wheat",
    "CORN": "Corn",
    "COTTON": "Cotton",
    "SUGAR": "Sugar",
    "COFFEE": "Coffee"
} 