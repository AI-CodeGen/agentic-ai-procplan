from typing import Dict, List, Optional, Tuple
import time
import logging
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.foreignexchange import ForeignExchange
from app.config import settings, llm
from app.agents.material_to_symbol_mapping import MATERIAL_TO_SYMBOL
from app.agents.av_commodity_map import ALPHA_VANTAGE_COMMODITIES
from app.agents.company_mapping import find_material_manufacturer
from langchain_core.prompts import ChatPromptTemplate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cache for storing prices
price_cache = {}
last_update_time = {}

# Cache for storing similarity mappings
similarity_cache = {}

# Cache for storing commodity mappings
commodity_mapping_cache = {}

# Cache for storing manufacturer mappings
manufacturer_mapping_cache = {}

# Rate limiting
RATE_LIMIT_DELAY = 12  # Alpha Vantage free tier allows 5 calls per minute
last_api_call = 0

def map_to_alpha_vantage_commodity(material: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Maps a material to the closest Alpha Vantage supported commodity using LLM.
    Returns a tuple of (symbol, commodity_name) or (None, None) if no match found.
    """
    try:
        # Check cache first
        if material in commodity_mapping_cache:
            logger.info(f"Using cached commodity mapping for {material}: {commodity_mapping_cache[material]}")
            return commodity_mapping_cache[material]

        # Create prompt for commodity mapping
        map_to_alpha_vantage_commodity_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a strict symbol matcher. Your ONLY task is to return a single symbol key.
            DO NOT provide any explanations, descriptions, or additional text.
            DO NOT return the commodity name.
            DO NOT add any context or reasoning.
            
            STRICT FORMAT RULES:
            1. Return ONLY the exact symbol key from the list below
            2. If no match found, return exactly: NONE
            3. DO NOT add any explanations or descriptions
            4. DO NOT return the commodity name
            5. ONLY return a single word response
            6. Match EXACTLY - if the material name matches a commodity name exactly, use that symbol
            7. DO NOT make assumptions or creative matches
            8. If the material name is not an exact match for any commodity name, return NONE
            
            Example correct responses:
            XAUUSD
            XAGUSD
            ALUMINUM
            NONE
            
            Example incorrect responses (DO NOT USE):
            ❌ Gold (XAUUSD)
            ❌ XAUUSD - Gold
            ❌ No match found
            ❌ XPDUSD (for Aluminum)
            
            Available symbols and commodities:
            {commodities}"""),
            ("human", "Return the symbol key for this material: {material}")
        ])

        # Format commodities list for the prompt
        commodities_list = "\n".join([f"{symbol}: {name}" for symbol, name in ALPHA_VANTAGE_COMMODITIES.items()])
        
        # Create chain
        chain = map_to_alpha_vantage_commodity_prompt | llm
        
        # Get response
        response = chain.invoke({
            "material": material,
            "commodities": commodities_list
        })
        
        # Clean and validate response
        mapped_symbol = response.strip().upper()  # Convert to uppercase for consistency
        logger.info(f"LLM response for {material}: {mapped_symbol}")
        
        # Check if the response is a valid symbol
        if mapped_symbol in ALPHA_VANTAGE_COMMODITIES:
            # Verify that the material name matches the commodity name
            commodity_name = ALPHA_VANTAGE_COMMODITIES[mapped_symbol]
            if material.lower() == commodity_name.lower():
                # Cache the result
                commodity_mapping_cache[material] = (mapped_symbol, commodity_name)
                logger.info(f"Mapped {material} to {commodity_name} ({mapped_symbol})")
                return mapped_symbol, commodity_name
            else:
                logger.warning(f"Symbol {mapped_symbol} found but material {material} doesn't match commodity {commodity_name}")
                return None, None
        
        logger.warning(f"No suitable Alpha Vantage commodity found for {material}")
        return None, None
            
    except Exception as e:
        logger.error(f"Error mapping material to commodity for {material}: {str(e)}")
        return None, None

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
        logger.info(f"Available materials for matching: {available_materials}")
        
        # Create chain
        chain = prompt | llm
        
        # Get response
        response = chain.invoke({
            "material": material,
            "materials": ", ".join(available_materials)
        })
        
        # Clean and validate response
        similar_material = response.strip()
        logger.info(f"LLM response for similar to {material}: {similar_material}")
        
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
    global last_api_call
    try:
        current_time = time.time()
        prices = {}
        
        # Initialize Alpha Vantage clients
        logger.info(f"Initializing Alpha Vantage clients with API key: {settings.ALPHA_VANTAGE_API_KEY[:4]}...")
        ts = TimeSeries(key=settings.ALPHA_VANTAGE_API_KEY, output_format='pandas')
        fx = ForeignExchange(key=settings.ALPHA_VANTAGE_API_KEY)
        
        for material in materials:
            logger.info(f"\nProcessing material: {material}")
            
            # Check if we have a cached price that's still valid
            if (material in price_cache and 
                material in last_update_time and 
                current_time - last_update_time[material] < settings.CACHE_EXPIRY):
                prices[material] = price_cache[material]
                logger.info(f"Using cached price for {material}: ${price_cache[material]}")
                continue
            
            # First try to map to Alpha Vantage commodity
            symbol, commodity_name = map_to_alpha_vantage_commodity(material)
            
            # If no direct Alpha Vantage mapping, try to find a manufacturer
            manufacturers = None
            if not symbol:
                logger.info(f"No direct Alpha Vantage mapping for {material}, looking for manufacturer")
                manufacturers = find_material_manufacturer(material, llm)
                if manufacturers and len(manufacturers) > 0:
                    # Use the first manufacturer from the list
                    symbol, company_name = manufacturers[0]
                    logger.info(f"Found manufacturer {company_name} ({symbol}) for {material}")
            
            # If still no mapping found, try the existing symbol mapping
            if not symbol:
                symbol = MATERIAL_TO_SYMBOL.get(material)
                logger.info(f"Direct symbol mapping for {material}: {symbol}")
                
                # If still no mapping found, try similarity matching
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
                # Rate limiting
                time_since_last_call = current_time - last_api_call
                if time_since_last_call < RATE_LIMIT_DELAY:
                    sleep_time = RATE_LIMIT_DELAY - time_since_last_call
                    logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                    time.sleep(sleep_time)
                
                # Get the latest price data
                logger.info(f"Next Step, Fetching price for {material} using symbol - {symbol}")
                
                # Try different endpoints based on the symbol type
                if symbol.startswith('X'):  # Forex symbols (e.g., XAUUSD)
                    logger.info(f"Getting exchange rate for {symbol}")
                    data, _ = fx.get_currency_exchange_rate(from_currency=symbol[:3], to_currency='USD')
                    latest_price = float(data['5. Exchange Rate'])
                else:  # Stock or commodity symbols
                    logger.info(f"Getting quote for {symbol}")
                    data, _ = ts.get_quote_endpoint(symbol=symbol)
                    # The API returns a pandas DataFrame with the price in the '05. price' column
                    if isinstance(data, pd.DataFrame) and not data.empty:
                        latest_price = float(data['05. price'].iloc[0])
                        logger.info(f"Quote price for {symbol}: ${latest_price}")
                    else:
                        raise ValueError(f"No price data available for {symbol}")
                
                last_api_call = time.time()
                logger.info(f"API Response for {material}: ${latest_price}")
                
                prices[material] = latest_price
                
                # Update cache
                price_cache[material] = latest_price
                last_update_time[material] = current_time
                logger.info(f"Updated price for {material}: ${latest_price}")
                
            except Exception as e:
                logger.error(f"Error fetching price for {material}: {str(e)}")
                # If we already have manufacturers from earlier, use them
                if manufacturers and len(manufacturers) > 0:
                    # Try the next manufacturer in the list
                    for symbol, company_name in manufacturers[1:]:
                        try:
                            # Rate limiting for the new API call
                            time_since_last_call = time.time() - last_api_call
                            if time_since_last_call < RATE_LIMIT_DELAY:
                                sleep_time = RATE_LIMIT_DELAY - time_since_last_call
                                logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                                time.sleep(sleep_time)
                            
                            # Try to get the manufacturer's stock price
                            data, _ = ts.get_quote_endpoint(symbol=symbol)
                            if isinstance(data, pd.DataFrame) and not data.empty:
                                latest_price = float(data['05. price'].iloc[0])
                                logger.info(f"Using manufacturer {company_name}'s stock price for {material}: ${latest_price}")
                                prices[material] = latest_price
                                # Update cache
                                price_cache[material] = latest_price
                                last_update_time[material] = current_time
                                break
                        except Exception as inner_e:
                            logger.error(f"Error fetching price for manufacturer {company_name}: {str(inner_e)}")
                            continue
                else:
                    logger.warning(f"No suitable price found for {material}, using default price")
                    prices[material] = 100.0
        
        return prices
        
    except Exception as e:
        logger.error(f"Error in get_market_prices: {str(e)}")
        return {material: 100.0 for material in materials}
