#!/usr/bin/env python3
"""
Test script for Wix sync endpoint
Run: python test_wix_sync.py [neighborhood_filter]

Examples:
  python test_wix_sync.py                    # Sync all neighborhoods
  python test_wix_sync.py "Midtown East"     # Sync only Midtown East
  python test_wix_sync.py "Brooklyn"         # Sync only Brooklyn | Queens
"""

import requests
import json
import sys
import os

# Local Flask app endpoint
API_URL = "http://localhost:5000/sync-wix"

def test_sync(neighborhood_filter=None):
    """Test the Wix sync endpoint"""
    print(f"\n{'='*60}")
    print("ROSIE AGENT E - Wix Sync Test")
    print(f"{'='*60}\n")
    
    if neighborhood_filter:
        print(f"Testing sync for: {neighborhood_filter}")
    else:
        print("Testing sync for: ALL NEIGHBORHOODS")
    
    print(f"Calling: POST {API_URL}\n")
    
    try:
        response = requests.post(API_URL, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        print("✓ SUCCESS!\n")
        print(json.dumps(result, indent=2))
        
        print(f"\n{'='*60}")
        print("Summary:")
        print(f"  Deals fetched:  {result.get('deals_fetched', 0)}")
        print(f"  Items built:    {result.get('items_built', 0)}")
        print(f"  Status:         {result.get('status', 'unknown')}")
        print(f"{'='*60}\n")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ ERROR: Could not connect to Flask app")
        print(f"  Make sure the Flask app is running on {API_URL}")
        return False
    except requests.exceptions.Timeout:
        print("✗ ERROR: Request timed out (took >60 seconds)")
        return False
    except requests.exceptions.HTTPError:
        print(f"✗ ERROR: HTTP {response.status_code}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
        return False
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    neighborhood = sys.argv[1] if len(sys.argv) > 1 else None
    success = test_sync(neighborhood)
    sys.exit(0 if success else 1)
