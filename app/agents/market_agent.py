from typing import Dict, List
import time
import logging
from alpha_vantage.timeseries import TimeSeries
from app.config import settings, llm
from app.agents.symbolMapping import MATERIAL_TO_SYMBOL
from langchain_core.prompts import ChatPromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for storing prices
price_cache = {}
last_update_time = {}

# Cache for storing similarity mappings
similarity_cache = {}

def find_similar_material(material: str) -> str:
    """Find a similar material from the mapping using LLM."""
    try:
        # Check cache first
        if material in similarity_cache:
            logger.info(f"Using cached similarity mapping for {material}: {similarity_cache[material]}")
            return similarity_cache[material]

        # Create prompt for similarity matching
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in material science and commodity markets.
            Given a material name, find the most similar material from the provided list.
            Return ONLY the exact material name from the list, nothing else.
            
            Available materials: {materials}"""),
            ("human", "Find the most similar material to: {material}")
        ])

        # Get list of available materials
        available_materials = list(MATERIAL_TO_SYMBOL.keys())
        
        # Create chain
        chain = prompt | llm
        
        # Get response
        response = chain.invoke({
            "material": material,
            "materials": ", ".join(available_materials)
        })
        
        # Clean and validate response
        similar_material = response.strip()
        if similar_material in MATERIAL_TO_SYMBOL:
            # Cache the result
            similarity_cache[material] = similar_material
            logger.info(f"Found similar material for {material}: {similar_material}")
            return similar_material
        else:
            logger.warning(f"LLM returned invalid material name: {similar_material}")
            return None
            
    except Exception as e:
        logger.error(f"Error finding similar material for {material}: {str(e)}")
        return None

def get_market_prices(materials: List[str]) -> Dict[str, float]:
    try:
        current_time = time.time()
        prices = {}
        
        # Initialize Alpha Vantage client
        ts = TimeSeries(key=settings.ALPHA_VANTAGE_API_KEY, output_format='pandas')
        
        for material in materials:
            # Check if we have a cached price that's still valid
            if (material in price_cache and 
                material in last_update_time and 
                current_time - last_update_time[material] < settings.CACHE_EXPIRY):
                prices[material] = price_cache[material]
                continue
            
            # Get the commodity symbol for the material
            symbol = MATERIAL_TO_SYMBOL.get(material)
            
            # If no direct mapping found, try similarity matching
            if not symbol:
                logger.info(f"No direct mapping found for {material}, attempting similarity matching")
                similar_material = find_similar_material(material)
                if similar_material:
                    symbol = MATERIAL_TO_SYMBOL[similar_material]
                    logger.info(f"Using symbol {symbol} from similar material {similar_material}")
                else:
                    logger.warning(f"No similar material found for {material}, using default price")
                    prices[material] = 100.0
                    continue
            
            try:
                # Get the latest price data
                data, meta_data = ts.get_intraday(symbol=symbol, interval='1min', outputsize='compact')
                if not data.empty:
                    latest_price = float(data['4. close'].iloc[0])
                    prices[material] = latest_price
                    
                    # Update cache
                    price_cache[material] = latest_price
                    last_update_time[material] = current_time
                    logger.info(f"Updated price for {material}: ${latest_price}")
                else:
                    logger.warning(f"No price data available for {material}, using default price")
                    prices[material] = 100.0  # Default price if no data available
            except Exception as e:
                logger.error(f"Error fetching price for {material}: {str(e)}")
                prices[material] = 100.0  # Default price on error
        
        return prices
        
    except Exception as e:
        logger.error(f"Error in get_market_prices: {str(e)}")
        # Return default prices in case of any error
        return {mat: 100.0 for mat in materials}
