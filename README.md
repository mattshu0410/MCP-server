# dbSNP MCP Plugin

This MCP plugin allows you to retrieve genetic variant information from NCBI's dbSNP database directly in your development environment.

## Features

- Retrieve detailed information about SNPs using rs IDs
- Search for SNPs by various terms (gene names, phenotypes, etc.)
- Get clinical significance information for variants

## Installation

### Prerequisites
- Python 3.7+
- MCP CLI tool

### Setup

1. Install the required dependencies:
```bash
pip install mcp requests
```

2. Install the MCP server:
```bash
mcp install server.py
```

3. (Optional) To use higher rate limits, get an NCBI API key and add it to your configuration:
```bash
mcp install server.py -v NCBI_API_KEY=your_api_key_here
```

## Usage

### Get SNP by rs ID
Retrieves detailed information about a specific SNP by its rs ID.

```python
# Example: Get details for rs6311
result = mcp.dbsnp.get_snp_by_rs("rs6311")
```

### Search for SNPs
Search for SNPs using various terms like gene names or phenotypes.

```python
# Example: Search for SNPs related to BRCA1
results = mcp.dbsnp.search_snps("BRCA1", limit=5)
```

### Get Clinical Significance
Retrieve clinical significance data for a specific SNP.

```python
# Example: Get clinical significance for rs397507444
clinical_data = mcp.dbsnp.get_snp_clinical_significance("rs397507444")
```

## Rate Limits

Without an API key, NCBI limits requests to 3 per second. With an API key, you can make up to 10 requests per second.

To obtain an NCBI API key:
1. Register for an NCBI account at https://www.ncbi.nlm.nih.gov/
2. Go to your account settings to generate an API key

## Troubleshooting

If you encounter issues:
- Check your internet connection
- Verify the rs ID format is correct
- Ensure your API key is valid (if using one)
- Check the error messages for specific API response issues

## License

MIT 