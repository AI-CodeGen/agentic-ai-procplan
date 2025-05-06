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

# Global cache for company data
_COMPANY_DATA_CACHE: Dict[str, str] = {}

def initialize_company_data() -> None:
    """
    Initialize the company data cache during server startup.
    This should be called once when the server starts.
    """
    global _COMPANY_DATA_CACHE
    if not _COMPANY_DATA_CACHE:
        _COMPANY_DATA_CACHE = load_company_data()
        logger.info(f"Initialized company data cache with {len(_COMPANY_DATA_CACHE)} companies")

def load_company_data() -> Dict[str, str]:
    """
    Load company data from NASDAQ and other listed files.
    Returns a dictionary mapping company names to their stock symbols.
    """
    companies = {}
    
    try:
        # Load NASDAQ listed companies
        with open('app/info/nasdaqlisted.txt', 'r') as f:
            reader = csv.reader(f, delimiter='|')
            next(reader)  # Skip header
            for row in reader:
                if len(row) >= 2:
                    symbol, name = row[0], row[1]
                    companies[name] = symbol
        
        # Load other listed companies
        with open('app/info/otherlisted.txt', 'r') as f:
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

def get_company_data() -> Dict[str, str]:
    """
    Get company data from cache. If cache is empty, load and cache the data.
    Returns a dictionary mapping company names to their stock symbols.
    """
    global _COMPANY_DATA_CACHE
    if not _COMPANY_DATA_CACHE:
        _COMPANY_DATA_CACHE = load_company_data()
    return _COMPANY_DATA_CACHE

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
        # Get company data from cache
        companies = get_company_data()
        if not companies:
            logger.error("No company data available")
            return []
            
        # Create prompt for manufacturer matching
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a strict data formatter. Your ONLY task is to return company names and their stock symbols.
            DO NOT provide any explanations, descriptions, or additional text.
            DO NOT modify the company names or symbols.
            DO NOT add any context or reasoning.
            DO NOT number the results.
            DO NOT add any dashes or other separators.
            DO NOT add any colons or other punctuation except the comma between company and symbol.
            DO NOT add any descriptions about the companies."""),
            ("system", f"""STRICT FORMAT RULES:
            1. Return EXACTLY {num_manufacturers} companies from the list below
            2. Each line MUST be in format: "Company Name, SYMBOL"
            3. Use ONLY companies from the provided list
            4. If no matches found, return exactly: NONE
            5. DO NOT add any numbers, dashes, or explanations
            6. DO NOT add any descriptions or explanations about the companies
            7. DO NOT add any introductory text
            
            Example correct response:
            Dow Inc., DOW
            DuPont, DD
            BASF, BASFY
            
            Example incorrect responses (DO NOT USE):
            ❌ Here are the manufacturers:
            ❌ BASF SE: BASF is a German chemical company
            ❌ Dow Inc. (DOW) - Chemical company
            ❌ Dow Inc. - DOW - Chemical manufacturer
            
            Available companies:
            {{companies}}"""),
            ("human", "Return {num_manufacturers} manufacturers for: {material}")
        ])
        
        # Format companies list for the prompt
        companies_list = "\n".join([f"{name} ({symbol})" for name, symbol in companies.items()])
        
        # Create chain
        chain = prompt | llm
        
        # Get response
        response = chain.invoke({
            "material": material,
            "companies": companies_list,
            "num_manufacturers": num_manufacturers
        })
        
        logger.info(f"LLM response for COMPANY MAPPING of {material}: {response}")
        
        # Clean and validate response
        matched_companies = []
        for line in response.strip().split('\n'):
            line = line.strip()
            if not line or line == 'NONE':
                continue
            # Skip any lines that look like explanations or introductions
            if any(skip in line.lower() for skip in ['here are', 'following', 'manufacturers of', 'companies that']):
                continue
            # Remove any leading numbers, dashes, or other separators
            line = line.lstrip('0123456789.- ')
            # Only accept lines that match the exact format
            if ',' in line and not any(char in line for char in ['(', ')', '-', ':', ';']):
                matched_companies.append(line)
            else:
                logger.warning(f"Skipping invalid format line: {line}")
        
        # Ensure we only take the requested number of manufacturers
        matched_companies = matched_companies[:num_manufacturers]
        logger.info(f"LLM response for MATCHED COMPANIES of {material}: {matched_companies}")
        
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