"""
Mapping of companies from NASDAQ and other exchanges to their stock symbols.
This mapping is used by the market agent to fetch real-time stock prices for material manufacturers.
"""

import csv
from typing import Dict, List, Tuple, Optional
import logging
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_company_data() -> Dict[str, str]:
    """
    Load company data from NASDAQ and other listed files.
    Returns a dictionary mapping company names to their stock symbols.
    """
    companies = {}
    
    try:
        # Load NASDAQ listed companies
        with open('app/nasdaqlisted.txt', 'r') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    symbol, name = row[0], row[1]
                    companies[name] = symbol
        
        # Load other listed companies
        with open('app/otherlisted.txt', 'r') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    symbol, name = row[0], row[1]
                    companies[name] = symbol
                    
        logger.info(f"Loaded {len(companies)} companies from exchange listings")
        return companies
        
    except Exception as e:
        logger.error(f"Error loading company data: {str(e)}")
        return {}

def find_material_manufacturer(material: str, llm, num_manufacturers: int = settings.No_OF_MANUFACTURERS) -> List[Tuple[Optional[str], Optional[str]]]:
    """
    Uses LLM to find the most likely manufacturers of a given material from the listed companies.
    Returns a list of tuples of (symbol, company_name) or empty list if no matches found.
    
    Args:
        material (str): The material to find manufacturers for
        llm: The language model to use for matching
        num_manufacturers (int): Number of manufacturers to return (default: 1)
    
    Returns:
        List[Tuple[Optional[str], Optional[str]]]: List of (symbol, company_name) tuples
    """
    try:
        # Load company data
        companies = load_company_data()
        if not companies:
            logger.error("No company data available")
            return []
            
        # Create prompt for manufacturer matching
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""You are an expert in manufacturing and materials science.
            Your task is to identify the {num_manufacturers} most likely manufacturers of a given material from the provided list of companies.
            
            CRITICAL INSTRUCTIONS:
            1. Return ONLY company names and their stock symbols from the list below, for one company per line
            2. DO NOT add any explanations, questions, or additional text
            3. DO NOT modify the company names in any way
            4. If no matches found, return exactly: NONE
            
            Example response format:
            Company Name 1, Stock Symbol 1 
            Company Name 2, Stock Symbol 2
            Company Name 3, Stock Symbol 3
            
            Available companies:
            {{companies}}"""),
            ("human", "Find the most likely manufacturers of this material: {material}")
        ])
        
        # Format companies list for the prompt
        companies_list = "\n".join([f"{name} ({symbol})" for name, symbol in companies.items()])
        
        # Create chain
        chain = prompt | llm
        
        # Get response
        response = chain.invoke({
            "material": material,
            "companies": companies_list
        })
        
        # Clean and validate response
        matched_companies = [company.strip() for company in response.strip().split('\n') if company.strip() and company.strip() != 'NONE']
        logger.info(f"LLM response for COMPANY MAPPING of {material}: {matched_companies}")
        
        # Find the symbols for the matched companies
        results = []
        logger.info(f"Attempting to match {len(matched_companies)} companies for {material}")
        
        for company_name in matched_companies:
            found_match = False
            logger.info(f"Looking for match: {company_name}")
            
            # First try exact match
            for name, symbol in companies.items():
                if name.lower() == company_name.lower():
                    logger.info(f"Found exact match: {name} ({symbol})")
                    results.append((symbol, name))
                    found_match = True
                    break
            
            # If no exact match, try partial match
            if not found_match:
                for name, symbol in companies.items():
                    if company_name.lower() in name.lower() or name.lower() in company_name.lower():
                        logger.info(f"Found partial match: {name} ({symbol}) for {company_name}")
                        results.append((symbol, name))
                        found_match = True
                        break
            
            if not found_match:
                logger.warning(f"No match found for company: {company_name}")
        
        if results:
            logger.info(f"Found {len(results)} manufacturers for {material}: {results}")
            return results
        
        logger.warning(f"No suitable manufacturers found for {material}")
        return []
            
    except Exception as e:
        logger.error(f"Error finding manufacturers for {material}: {str(e)}")
        return []

# Major manufacturing companies grouped by material categories
MANUFACTURING_COMPANIES = {
    # Metals & Mining
    "BHP": "BHP Group (Mining & Metals)",
    "RIO": "Rio Tinto (Mining & Metals)",
    "VALE": "Vale S.A. (Mining & Metals)",
    "FCX": "Freeport-McMoRan (Copper & Gold)",
    "NEM": "Newmont Corporation (Gold)",
    "AA": "Alcoa Corporation (Aluminum)",
    "X": "United States Steel (Steel)",
    "NUE": "Nucor Corporation (Steel)",
    "STLD": "Steel Dynamics (Steel)",
    
    # Chemicals & Materials
    "DD": "DuPont (Chemicals & Materials)",
    "DOW": "Dow Inc. (Chemicals & Materials)",
    "BASFY": "BASF (Chemicals & Materials)",
    "LYB": "LyondellBasell (Chemicals & Plastics)",
    "ECL": "Ecolab (Chemicals & Cleaning)",
    "SHW": "Sherwin-Williams (Paints & Coatings)",
    
    # Electronics & Semiconductors
    "INTC": "Intel (Semiconductors)",
    "TSM": "Taiwan Semiconductor (Semiconductors)",
    "AMD": "Advanced Micro Devices (Semiconductors)",
    "NVDA": "NVIDIA (Semiconductors)",
    "QCOM": "Qualcomm (Semiconductors)",
    "MU": "Micron Technology (Memory)",
    
    # Energy & Oil
    "XOM": "Exxon Mobil (Oil & Gas)",
    "CVX": "Chevron (Oil & Gas)",
    "COP": "ConocoPhillips (Oil & Gas)",
    "EOG": "EOG Resources (Oil & Gas)",
    "PXD": "Pioneer Natural Resources (Oil & Gas)",
    
    # Construction Materials
    "VMC": "Vulcan Materials (Construction Materials)",
    "MLM": "Martin Marietta Materials (Construction Materials)",
    "SUM": "Summit Materials (Construction Materials)",
    "CRH": "CRH plc (Building Materials)",
    "CEMEX": "CEMEX (Cement & Construction)",
    
    # Specialty Materials
    "ALB": "Albemarle (Lithium & Specialty Chemicals)",
    "LTHM": "Livent Corporation (Lithium)",
    "SQM": "Sociedad Química y Minera (Lithium & Iodine)",
    "FMC": "FMC Corporation (Agricultural Chemicals)",
    "MOS": "Mosaic Company (Fertilizers & Minerals)",
    
    # Glass & Ceramics
    "GLW": "Corning (Glass & Ceramics)",
    "OC": "Owens Corning (Building Materials)",
    "APOG": "Apogee Enterprises (Glass Products)",
    
    # Plastics & Polymers
    "EMN": "Eastman Chemical (Plastics & Polymers)",
    "WLK": "Westlake Chemical (Plastics & Polymers)",
    "HUN": "Huntsman Corporation (Plastics & Chemicals)",
    
    # Battery Materials
    "LAC": "Lithium Americas (Lithium)",
    "PLL": "Piedmont Lithium (Lithium)",
    "MP": "MP Materials (Rare Earth Elements)",
    "REE": "Rare Element Resources (Rare Earth Elements)",
    
    # Industrial Gases
    "APD": "Air Products & Chemicals (Industrial Gases)",
    "LIN": "Linde plc (Industrial Gases)",
    "PRAX": "Praxair (Industrial Gases)"
} 