#!/usr/bin/env python3
import mcp
import json
from time import sleep

def pretty_print(data):
    """Print data in a nicely formatted way"""
    print(json.dumps(data, indent=2))
    print("-" * 50)

def test_get_snp_by_rs():
    """Test retrieving SNP data by rs ID"""
    print("\n🧪 TESTING get_snp_by_rs function:")
    
    # Test with a common SNP
    rs_id = "rs6311"
    print(f"Querying data for {rs_id}...")
    result = mcp.dbsnp.get_snp_by_rs(rs_id)
    
    # Check for success
    if result.get("success"):
        print(f"✅ SUCCESS: Retrieved data for {rs_id}")
        # Print only selected parts to avoid overwhelming output
        data = result.get("data", {})
        refsnp_id = data.get("refsnp_id")
        chromosome = data.get("primary_snapshot_data", {}).get("placements_with_allele", [{}])[0].get("placement", {}).get("seq_id_traits_by_assembly", [{}])[0].get("seq_id_traits", {}).get("name")
        print(f"RefSNP ID: {refsnp_id}")
        print(f"Chromosome: {chromosome}")
    else:
        print(f"❌ ERROR: Failed to retrieve data for {rs_id}")
        pretty_print(result)
    
    # Add a small delay to respect rate limits
    sleep(1)
    
    return result.get("success", False)

def test_search_snps():
    """Test searching for SNPs"""
    print("\n🧪 TESTING search_snps function:")
    
    # Test with a gene name
    term = "BRCA1"
    limit = 3
    print(f"Searching for SNPs related to '{term}' with limit {limit}...")
    result = mcp.dbsnp.search_snps(term, limit)
    
    # Check for success
    if result.get("success"):
        print(f"✅ SUCCESS: Found {result.get('total_count')} SNPs related to '{term}'")
        print(f"Results returned: {len(result.get('results', []))}")
        # Print the first few results
        for i, snp in enumerate(result.get("results", [])[:3]):
            print(f"  {i+1}. {snp.get('rs_id')}")
    else:
        print(f"❌ ERROR: Failed to search for '{term}'")
        pretty_print(result)
    
    # Add a small delay to respect rate limits
    sleep(1)
    
    return result.get("success", False)

def test_get_snp_clinical_significance():
    """Test retrieving clinical significance data"""
    print("\n🧪 TESTING get_snp_clinical_significance function:")
    
    # Test with a clinically significant variant
    rs_id = "rs397507444"  # BRCA1 pathogenic variant
    print(f"Querying clinical significance for {rs_id}...")
    result = mcp.dbsnp.get_snp_clinical_significance(rs_id)
    
    # Check for success
    if result.get("success"):
        print(f"✅ SUCCESS: Retrieved clinical data for {rs_id}")
        clinical_data = result.get("clinical_significance", [])
        if isinstance(clinical_data, list) and clinical_data:
            print(f"Found {len(clinical_data)} clinical annotations")
            # Show first annotation as example
            if clinical_data[0].get("clinical_significance"):
                print(f"Clinical significance: {clinical_data[0].get('clinical_significance')}")
                print(f"Review status: {clinical_data[0].get('review_status')}")
                diseases = clinical_data[0].get("disease_names", [])
                if diseases:
                    print(f"Associated with: {diseases[0]}")
        else:
            print(f"No clinical data found for {rs_id}")
    else:
        print(f"❌ ERROR: Failed to retrieve clinical data for {rs_id}")
        pretty_print(result)
    
    return result.get("success", False)

def run_all_tests():
    """Run all tests and report results"""
    print("=" * 50)
    print("DBSNP MCP PLUGIN TEST SUITE")
    print("=" * 50)
    
    # Track test results
    test_results = {
        "get_snp_by_rs": False,
        "search_snps": False,
        "get_snp_clinical_significance": False
    }
    
    # Run tests
    test_results["get_snp_by_rs"] = test_get_snp_by_rs()
    test_results["search_snps"] = test_search_snps()
    test_results["get_snp_clinical_significance"] = test_get_snp_clinical_significance()
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! The dbSNP MCP plugin is working correctly.")
    else:
        print("\n⚠️ SOME TESTS FAILED. Please check the error messages above.")

if __name__ == "__main__":
    run_all_tests() 