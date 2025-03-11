from typing import Any, Dict, List, Optional, Union
import httpx
import logging
from mcp.server.fastmcp import FastMCP, Context
from metapub import PubMedFetcher, convert, FindIt
import os
import tempfile
import pymupdf4llm
from pathlib import Path
import aiofiles
import asyncio
from urllib.parse import urlparse, quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server and fetchers
mcp = FastMCP("dbSNP")
pubmed_fetch = PubMedFetcher()

# Constants
NWS_API_BASE = "https://clinicaltables.nlm.nih.gov/api/snps/v3/search"
USER_AGENT = "dbsnp-app/1.0"

# Define the fields we want to retrieve
DISPLAY_FIELDS = [
    'rsNum',
    '38.chr', '38.pos', '38.alleles', '38.gene', '38.assembly',
    '37.chr', '37.pos', '37.alleles', '37.gene', '37.assembly'
]

async def fetch_snp_data(query: str) -> Dict[str, Any]:
    """Helper function to fetch SNP data from the API"""
    logger.info(f"[API] Fetching SNP data for query: {query}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                NWS_API_BASE,
                params={
                    "terms": query,
                    "df": ",".join(DISPLAY_FIELDS)
                },
                headers={"User-Agent": USER_AGENT}
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"[API] Successfully fetched data for {query}")
            return data
    except httpx.HTTPError as e:
        logger.error(f"[Error] HTTP error occurred: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"[Error] Unexpected error: {str(e)}")
        raise

def format_snp_data(item: List[str]) -> str:
    """Format SNP data into a readable string"""
    if len(item) != len(DISPLAY_FIELDS):
        return f"SNP ID: {item[0]} (incomplete data)"
    
    data = dict(zip(DISPLAY_FIELDS, item))
    
    # Format GRCh38 data
    grch38_info = [
        f"GRCh38 Assembly:",
        f"  Chromosome: {data['38.chr']}",
        f"  Position: {data['38.pos']}",
        f"  Alleles: {data['38.alleles']}",
        f"  Gene: {data['38.gene'] or 'Not specified'}"
    ]
    
    # Format GRCh37 data
    grch37_info = [
        f"GRCh37 Assembly:",
        f"  Chromosome: {data['37.chr']}",
        f"  Position: {data['37.pos']}",
        f"  Alleles: {data['37.alleles']}",
        f"  Gene: {data['37.gene'] or 'Not specified'}"
    ]
    
    # Combine all information
    return "\n".join([
        f"SNP ID: {data['rsNum']}",
        "",
        *grch38_info,
        "",
        *grch37_info
    ])

@mcp.tool()
async def search_snp(query: str) -> str:
    """
    Search for SNP information by rsID or genomic location.
    
    Args:
        query: SNP identifier (e.g., rs1234) or genomic location
    
    Returns:
        Formatted string containing comprehensive SNP information for both assemblies
    """
    try:
        data = await fetch_snp_data(query)
        if not data or len(data) < 4 or not data[3]:
            return f"No SNP information found for query: {query}"
        
        results = []
        for item in data[3]:
            results.append(format_snp_data(item))
        
        total_results = data[0]
        summary = f"Found {total_results} matching SNPs. Showing first {len(results)}:\n\n"
        return summary + "\n\n==========\n\n".join(results)
    except Exception as e:
        return f"Error searching for SNP: {str(e)}"

@mcp.resource("snp://{rsid}")
async def get_snp_info(rsid: str) -> str:
    """
    Get detailed information about a specific SNP by rsID.
    
    Args:
        rsid: SNP identifier (e.g., rs1234)
    
    Returns:
        Detailed SNP information as a string, including data from both assemblies
    """
    try:
        data = await fetch_snp_data(rsid)
        if not data or len(data) < 4 or not data[3]:
            return f"No information found for SNP: {rsid}"
        
        # Return first match details
        return format_snp_data(data[3][0])
    except Exception as e:
        return f"Error retrieving SNP information: {str(e)}"

@mcp.prompt()
def snp_lookup_help() -> str:
    """Provide help information for SNP lookups"""
    return """
    To look up SNP information, you can:
    1. Search for SNPs using the search_snp tool with a query
    2. Get specific SNP details using the snp://{rsid} resource
    
    The information returned includes:
    - SNP ID (rsNum)
    - GRCh38 Assembly data:
      * Chromosome location
      * Position
      * Alleles
      * Associated gene
    - GRCh37 Assembly data:
      * Chromosome location
      * Position
      * Alleles
      * Associated gene
    
    Examples:
    - search_snp("rs1234")
    - Resource: snp://rs1234
    """

@mcp.tool()
async def get_articles(dois: List[str]) -> str:
    """
    Comprehensive article information retrieval tool. For each DOI, returns:
    - Basic article metadata (title, authors, journal, etc.)
    - Full abstract
    - Full text URL (if available)
    
    Args:
        dois: List of Digital Object Identifiers
    
    Returns:
        Formatted string containing complete information for all articles,
        including any errors encountered during processing
    """
    results = []
    for doi in dois:
        try:
            logger.info(f"[Article] Processing DOI: {doi}")
            article_info = [
                "Article Information:",
                f"DOI: {doi}"
            ]
            
            # Get PMID
            try:
                pmid = convert.doi2pmid(doi)
                if not pmid:
                    raise ValueError("Could not convert DOI to PMID")
                article_info.append(f"PMID: {pmid}")
            except Exception as e:
                logger.error(f"[Error] Failed to get PMID for DOI {doi}: {str(e)}")
                article_info.append(f"Error: Could not retrieve PMID - {str(e)}")
                results.append("\n".join(article_info))
                continue
                
            # Fetch article information
            try:
                article = pubmed_fetch.article_by_pmid(pmid)
                if not article:
                    raise ValueError("No article data returned")
                
                # Basic metadata
                article_info.extend([
                    f"Title: {article.title}",
                    f"Authors: {'; '.join(article.authors)}",
                    f"Journal: {article.journal} ({article.year})",
                    f"Citation: {article.citation}"
                ])
                
                # Abstract
                article_info.extend([
                    "",
                    "Abstract:",
                    article.abstract if article.abstract else "Not available"
                ])
            except Exception as e:
                logger.error(f"[Error] Failed to fetch article data for PMID {pmid}: {str(e)}")
                article_info.append(f"Error: Could not retrieve article data - {str(e)}")
                results.append("\n".join(article_info))
                continue
            
            # Full text URL
            try:
                finder = FindIt(pmid)
                article_info.extend([
                    "",
                    "Full Text Access:"
                ])
                if finder.url:
                    article_info.append(f"URL: {finder.url}")
                else:
                    article_info.extend([
                        "Full text URL not available",
                        f"Reason: {finder.reason}"
                    ])
            except Exception as e:
                logger.error(f"[Error] Failed to find full text for PMID {pmid}: {str(e)}")
                article_info.extend([
                    "",
                    "Full Text Access:",
                    f"Error: Could not retrieve full text URL - {str(e)}"
                ])
            
            results.append("\n".join(article_info))
            
        except Exception as e:
            # Catch any unexpected errors for this DOI
            logger.error(f"[Error] Unexpected error processing DOI {doi}: {str(e)}")
            results.append(f"Failed to process DOI: {doi}\nError: {str(e)}")
    
    # Return results with clear separation between articles
    if not results:
        return "No articles were processed successfully."
    
    return "\n\n==========\n\n".join(results)

@mcp.tool()
async def get_full_text_markdown(dois: List[str]) -> str:
    """
    Downloads open access PDFs using Unpaywall API and converts them to markdown text.
    
    Args:
        dois: List of Digital Object Identifiers
        
    Returns:
        Formatted string containing markdown text for each successfully processed PDF,
        with error messages for any failures
    """
    results = []
    temp_dir = tempfile.mkdtemp(prefix="pdf_processing_")
    email = "matthews1000140@gmail.com"  # Required for Unpaywall API
    
    try:
        async with httpx.AsyncClient() as client:
            for doi in dois:
                try:
                    logger.info(f"[PDF] Processing DOI: {doi}")
                    result_info = [
                        "PDF Processing Results:",
                        f"DOI: {doi}"
                    ]
                    
                    # Query Unpaywall API
                    try:
                        unpaywall_url = f"https://api.unpaywall.org/v2/{quote(doi)}?email={email}"
                        response = await client.get(unpaywall_url)
                        response.raise_for_status()
                        data = response.json()
                        
                        # Check if there's an open access PDF
                        best_oa_location = None
                        if data.get("is_oa", False):
                            # Try to find best PDF URL from available OA locations
                            oa_locations = data.get("oa_locations", [])
                            for location in oa_locations:
                                if location.get("url_for_pdf"):
                                    best_oa_location = location
                                    break
                            if not best_oa_location and oa_locations:
                                # Fallback to first location with any URL
                                best_oa_location = oa_locations[0]
                        
                        if not best_oa_location:
                            raise ValueError("No open access PDF available")
                        
                        pdf_url = best_oa_location.get("url_for_pdf") or best_oa_location.get("url")
                        if not pdf_url:
                            raise ValueError("No PDF URL found in open access location")
                        
                        # Create a safe filename
                        filename = os.path.join(temp_dir, f"{doi.replace('/', '_')}.pdf")
                        
                        # Download PDF
                        pdf_response = await client.get(pdf_url, follow_redirects=True)
                        pdf_response.raise_for_status()
                        
                        # Verify it's a PDF
                        content_type = pdf_response.headers.get('content-type', '')
                        if 'pdf' not in content_type.lower():
                            raise ValueError(f"Not a PDF file (content-type: {content_type})")
                        
                        # Save PDF
                        async with aiofiles.open(filename, 'wb') as f:
                            await f.write(pdf_response.content)
                        
                        # Convert to markdown
                        md_text = pymupdf4llm.to_markdown(filename)
                        
                        result_info.extend([
                            f"Open Access Source: {best_oa_location.get('host_type', 'unknown')}",
                            "",
                            "Markdown Content:",
                            md_text
                        ])
                        
                    except httpx.HTTPError as e:
                        logger.error(f"[Error] API or download error for DOI {doi}: {str(e)}")
                        result_info.append(f"Error: Failed to retrieve or download PDF - {str(e)}")
                    except Exception as e:
                        logger.error(f"[Error] Failed to process PDF for DOI {doi}: {str(e)}")
                        result_info.append(f"Error: Failed to process PDF - {str(e)}")
                    finally:
                        # Clean up the temporary file if it exists
                        if os.path.exists(filename):
                            os.remove(filename)
                            
                except Exception as e:
                    # Catch any unexpected errors for this DOI
                    logger.error(f"[Error] Unexpected error processing DOI {doi}: {str(e)}")
                    result_info = [
                        "PDF Processing Results:",
                        f"DOI: {doi}",
                        f"Error: {str(e)}"
                    ]
                
                results.append("\n".join(result_info))
    
    finally:
        # Clean up temporary directory
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            logger.error(f"[Error] Failed to clean up temporary directory: {str(e)}")
    
    # Return results with clear separation between PDFs
    if not results:
        return "No PDFs were processed successfully."
    
    return "\n\n==========\n\n".join(results)

if __name__ == "__main__":
    import asyncio
    import sys

    # Configure logging to stderr for Claude Desktop
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    try:
        # Initialize and run the server
        asyncio.run(mcp.run(transport='stdio'))
    except Exception as e:
        logger.error(f"Server failed to start: {str(e)}")
        sys.exit(1)