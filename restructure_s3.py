#!/usr/bin/env python3
"""
Script to restructure S3 folders from address-based to deal ID-based naming.
Maps Brooklyn | Queens and West Village address folders to numeric deal IDs from Pipedrive.
"""

import boto3
import os
import requests
from collections import defaultdict

# Initialize AWS S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

BUCKET_NAME = 'neighborhood-listing-images'
PIPEDRIVE_TOKEN = os.environ.get('PIPEDRIVE_API_TOKEN')

def list_neighborhood_folders(neighborhood):
    """List all folders in a specific neighborhood"""
    prefix = f'Neighborhood Listing Images/{neighborhood}/'
    
    paginator = s3.get_paginator('list_objects_v2')
    folders = set()
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix, Delimiter='/'):
        for common_prefix in page.get('CommonPrefixes', []):
            folder_path = common_prefix['Prefix']
            # Extract folder name (deal ID or address)
            folder_name = folder_path.replace(prefix, '').rstrip('/')
            if folder_name:  # Skip empty
                folders.add(folder_name)
    
    return sorted(folders)

def search_pipedrive_deal(address):
    """Search Pipedrive for deal by address"""
    if not PIPEDRIVE_TOKEN:
        return None
    
    try:
        response = requests.get(
            "https://api.pipedrive.com/v1/deals",
            params={
                "api_token": PIPEDRIVE_TOKEN,
                "term": address,
                "limit": 5
            }
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        
        if data and "items" in data:
            for item in data["items"]:
                deal = item.get("item", {})
                deal_id = deal.get("id")
                title = deal.get("title", "")
                
                # Check if this is a good match
                if address.lower() in title.lower():
                    return {"id": deal_id, "title": title}
        
        return None
    except Exception as e:
        print(f"Error searching Pipedrive for '{address}': {e}")
        return None

def analyze_neighborhoods():
    """Analyze Brooklyn | Queens and West Village folders"""
    neighborhoods = ["Brooklyn | Queens", "UnSQ:Gren'Villl."]
    
    mapping = {}
    
    for neighborhood in neighborhoods:
        print(f"\n{'='*60}")
        print(f"Analyzing: {neighborhood}")
        print('='*60)
        
        folders = list_neighborhood_folders(neighborhood)
        print(f"Found {len(folders)} folders\n")
        
        mapping[neighborhood] = {}
        
        for folder in folders:
            # Check if already numeric (shouldn't be, but handle it)
            try:
                int(folder)
                print(f"✓ {folder} - Already numeric (skipping)")
                continue
            except ValueError:
                pass
            
            # Search Pipedrive
            print(f"Searching Pipedrive for: {folder}...", end=" ")
            result = search_pipedrive_deal(folder)
            
            if result:
                print(f"✓ Found Deal #{result['id']} - {result['title']}")
                mapping[neighborhood][folder] = {
                    "deal_id": result['id'],
                    "deal_title": result['title']
                }
            else:
                print(f"✗ NOT FOUND")
                mapping[neighborhood][folder] = None
    
    return mapping

def display_mapping(mapping):
    """Display the mapping for user review"""
    print("\n" + "="*80)
    print("PROPOSED S3 FOLDER RESTRUCTURING")
    print("="*80)
    
    total_found = 0
    total_missing = 0
    
    for neighborhood, folders in mapping.items():
        print(f"\n{neighborhood}:")
        print("-" * 80)
        
        for address, deal_info in folders.items():
            if deal_info:
                old_path = f"Neighborhood Listing Images/{neighborhood}/{address}/"
                new_path = f"Neighborhood Listing Images/{neighborhood}/{deal_info['deal_id']}/"
                print(f"  {address:40} → {deal_info['deal_id']:6} ({deal_info['deal_title']})")
                total_found += 1
            else:
                print(f"  {address:40} → NOT FOUND ⚠️")
                total_missing += 1
    
    print("\n" + "="*80)
    print(f"Summary: {total_found} folders can be renamed, {total_missing} need manual review")
    print("="*80)
    
    return total_found, total_missing

if __name__ == "__main__":
    print("Analyzing S3 folder structure...\n")
    
    # Analyze and get mapping
    mapping = analyze_neighborhoods()
    
    # Display results
    total_found, total_missing = display_mapping(mapping)
    
    if total_missing > 0:
        print(f"\n⚠️  WARNING: {total_missing} folders could not be mapped to Pipedrive deals.")
        print("These will need manual review before restructuring.")
