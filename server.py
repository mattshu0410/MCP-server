#!/usr/bin/env python3
import os
import sys
import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union
from mcp import Server, attempt_completion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("dbsnp-mcp")

# Initialize MCP server
server = Server()

# Constants
BASE_URL = "https://api.ncbi.nlm.nih.gov/variation/v0"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Add API key if provided
api_key = os.environ.get("NCBI_API_KEY")
if api_key:
    HEADERS["api-key"] = api_key
    logger.info("[Setup] NCBI API key configured")
else:
    logger.info("[Setup] Running without NCBI API key (rate limits will be lower)")

def handle_api_error(response: requests.Response) -> Dict[str, Any]:
    """Handle API errors with appropriate logging and formatted response"""
    try:
        error_data = response.json()
    except:
        error_data = {"raw_text": response.text}
    
    logger.error(f"[API] Error {response.status_code}: {json.dumps(error_data)}")
    return {
        "success": False,
        "status_code": response.status_code,
        "error": error_data
    }

@server.function("get_snp_by_rs")
def get_snp_by_rs(rs_id: str) -> Dict[str, Any]:
    """
    Retrieve SNP data for a specific rs ID from dbSNP.
    
    Args:
        rs_id: The rs ID of the SNP (e.g., "rs6311", "rs1234")
    
    Returns:
        Dictionary containing SNP data or error information
    """
    # Normalize rs_id format (remove 'rs' prefix if present and add it back)
    rs_number = rs_id.lower().replace("rs", "")
    normalized_rs_id = f"rs{rs_number}"
    
    logger.info(f"[API] Requesting SNP data for {normalized_rs_id}")
    
    url = f"{BASE_URL}/refsnp/{normalized_rs_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"[API] Successfully retrieved data for {normalized_rs_id}")
            return {
                "success": True,
                "data": data,
                "rs_id": normalized_rs_id
            }
        else:
            return handle_api_error(response)
    
    except Exception as e:
        logger.error(f"[Error] Failed to retrieve SNP data: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@server.function("search_snps")
def search_snps(term: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search for SNPs using the NCBI esearch endpoint.
    
    Args:
        term: Search term (e.g., "BRCA1", "HTN", "rs6311")
        limit: Maximum number of results to return (default: 10)
    
    Returns:
        Dictionary containing search results or error information
    """
    logger.info(f"[API] Searching SNPs with term: {term}, limit: {limit}")
    
    # Using NCBI eutils for searching
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "snp",
        "term": term,
        "retmode": "json",
        "retmax": limit
    }
    
    if api_key:
        params["api_key"] = api_key
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"[API] Successfully retrieved search results for '{term}'")
            
            # Get details for each SNP if IDs are available
            id_list = data.get("esearchresult", {}).get("idlist", [])
            snp_details = []
            
            if id_list:
                for snp_id in id_list[:limit]:
                    # Convert numeric ID to rs ID
                    rs_id = f"rs{snp_id}"
                    # Get basic info (not full data to keep response size manageable)
                    snp_details.append({
                        "rs_id": rs_id,
                        "numeric_id": snp_id
                    })
            
            return {
                "success": True,
                "search_term": term,
                "total_count": int(data.get("esearchresult", {}).get("count", 0)),
                "returned_count": len(id_list),
                "results": snp_details
            }
        else:
            return handle_api_error(response)
    
    except Exception as e:
        logger.error(f"[Error] Failed to search SNPs: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@server.function("get_snp_clinical_significance")
def get_snp_clinical_significance(rs_id: str) -> Dict[str, Any]:
    """
    Retrieve clinical significance data for a specific rs ID.
    
    Args:
        rs_id: The rs ID of the SNP (e.g., "rs6311", "rs1234")
    
    Returns:
        Dictionary containing clinical significance data or error information
    """
    # Normalize rs_id format
    rs_number = rs_id.lower().replace("rs", "")
    normalized_rs_id = f"rs{rs_number}"
    
    logger.info(f"[API] Requesting clinical significance data for {normalized_rs_id}")
    
    # First, get the full SNP data
    full_data_result = get_snp_by_rs(normalized_rs_id)
    
    if not full_data_result.get("success", False):
        return full_data_result
    
    # Extract clinical significance from the data
    data = full_data_result.get("data", {})
    clinical_info = []
    
    try:
        # Parse through potentially complex data structure to find clinical significance
        allele_annotations = data.get("primary_snapshot_data", {}).get("allele_annotations", [])
        
        for annotation in allele_annotations:
            for clinical_annotation in annotation.get("clinical", []):
                clinical_info.append({
                    "accession": clinical_annotation.get("accession"),
                    "clinical_significance": clinical_annotation.get("clinical_significance"),
                    "disease_names": [d.get("name") for d in clinical_annotation.get("disease_names", [])],
                    "review_status": clinical_annotation.get("review_status")
                })
        
        logger.info(f"[API] Successfully extracted clinical data for {normalized_rs_id}")
        return {
            "success": True,
            "rs_id": normalized_rs_id,
            "clinical_significance": clinical_info if clinical_info else "No clinical significance data found"
        }
        
    except Exception as e:
        logger.error(f"[Error] Failed to parse clinical significance: {str(e)}")
        return {
            "success": False,
            "rs_id": normalized_rs_id,
            "error": f"Failed to parse clinical data: {str(e)}"
        }

# Start the server
if __name__ == "__main__":
    logger.info("[Setup] Starting dbSNP MCP server...")
    server.start() 