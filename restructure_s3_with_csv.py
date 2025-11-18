#!/usr/bin/env python3
"""
Script to restructure S3 folders using Pipedrive CSV mapping.
Matches S3 folder names (addresses) to deal IDs and renames folders.
"""

import boto3
import os
import csv
import re
from difflib import SequenceMatcher

# Initialize AWS S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

BUCKET_NAME = 'neighborhood-listing-images'

def normalize_address(address):
    """Normalize address for fuzzy matching"""
    # Remove common suffixes
    normalized = address.replace(' copy', '').replace('**', '').replace('*', '')
    
    # Standardize street abbreviations (aggressive)
    normalized = normalized.replace(' St,', ' Street,').replace(' St ', ' Street ').replace(' St.', ' Street')
    normalized = normalized.replace(' Ave,', ' Avenue,').replace(' Ave ', ' Avenue ').replace(' Ave.', ' Avenue')
    normalized = normalized.replace(' Brdwy', ' Broadway').replace(' Blvd', ' Boulevard')
    normalized = normalized.replace(' Pl', ' Place')
    
    # Standardize direction abbreviations
    normalized = normalized.replace(' E ', ' East ').replace(' W ', ' West ')
    normalized = normalized.replace(' N ', ' North ').replace(' S ', ' South ')
    
    # Standardize location abbreviations
    normalized = normalized.replace('Bklyn', 'Brooklyn').replace('Qns', 'Queens').replace('SI', 'Staten Island')
    normalized = normalized.replace('Hts', 'Heights').replace("Downt'", 'Downtown')
    normalized = normalized.replace('Un Sq', 'Union Square').replace('UnSq', 'Union Square')
    
    # Remove parenthetical details for broader matching
    normalized = re.sub(r'\([^)]*\)', '', normalized)
    
    # Remove special characters
    normalized = normalized.replace('#', '').replace(',', '')
    
    # Remove extra spaces
    normalized = ' '.join(normalized.split())
    return normalized.strip()

def similarity_score(str1, str2):
    """Calculate similarity between two strings (0-1)"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def load_csv_mapping(csv_path):
    """Load address -> deal_id mapping from CSV"""
    mapping = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            deal_id = row.get('Deal - ID', '').strip()
            address = row.get('Deal - Neighborhood (address details)', '').strip()
            
            if deal_id and address:
                address_clean = address.replace('**', '').replace('*', '')
                mapping[address_clean] = deal_id
    
    return mapping

def find_best_match(folder_name, csv_mapping, manual_overrides=None):
    """Find best matching deal ID for a folder name"""
    # Check manual overrides first
    if manual_overrides and folder_name in manual_overrides:
        deal_id = manual_overrides[folder_name]
        if deal_id == "DELETE":
            return "DELETE", 1.0, "manual_deletion"
        return deal_id, 1.0, "manual_override"
    
    normalized_folder = normalize_address(folder_name)
    
    # Try exact match first
    if normalized_folder in csv_mapping:
        return csv_mapping[normalized_folder], 1.0, "exact"
    
    # Try fuzzy matching
    best_match = None
    best_score = 0.0
    best_address = None
    
    for csv_address, deal_id in csv_mapping.items():
        normalized_csv = normalize_address(csv_address)
        score = similarity_score(normalized_folder, normalized_csv)
        
        if score > best_score:
            best_score = score
            best_match = deal_id
            best_address = csv_address
    
    # Only accept matches with high confidence (>0.7)
    if best_score >= 0.7:
        return best_match, best_score, best_address
    
    return None, 0.0, None

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

def rename_s3_folder(neighborhood, old_name, new_name):
    """Rename a folder in S3 by copying all objects to new prefix"""
    old_prefix = f'Neighborhood Listing Images/{neighborhood}/{old_name}/'
    new_prefix = f'Neighborhood Listing Images/{neighborhood}/{new_name}/'
    
    # List all objects in old folder
    paginator = s3.get_paginator('list_objects_v2')
    objects = []
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=old_prefix):
        for obj in page.get('Contents', []):
            objects.append(obj['Key'])
    
    if not objects:
        print(f"  WARNING: No objects found in {old_prefix}")
        return False
    
    # Copy each object to new location
    for old_key in objects:
        # Calculate new key
        relative_path = old_key.replace(old_prefix, '')
        new_key = new_prefix + relative_path
        
        # Copy object
        copy_source = {'Bucket': BUCKET_NAME, 'Key': old_key}
        s3.copy_object(CopySource=copy_source, Bucket=BUCKET_NAME, Key=new_key)
        print(f"    Copied: {old_key} -> {new_key}")
    
    # Delete old objects
    for old_key in objects:
        s3.delete_object(Bucket=BUCKET_NAME, Key=old_key)
        print(f"    Deleted: {old_key}")
    
    return True

def analyze_and_map(csv_path, manual_overrides=None):
    """Analyze folders and create mapping"""
    csv_mapping = load_csv_mapping(csv_path)
    print(f"Loaded {len(csv_mapping)} deals from CSV\n")
    
    if manual_overrides:
        print(f"Manual overrides provided: {len(manual_overrides)} folders\n")
    
    neighborhoods = ["Brooklyn | Queens", "UnSQ:Gren'Villl."]
    
    all_mappings = {}
    
    for neighborhood in neighborhoods:
        print(f"\n{'='*80}")
        print(f"Analyzing: {neighborhood}")
        print('='*80)
        
        folders = list_neighborhood_folders(neighborhood)
        print(f"Found {len(folders)} folders\n")
        
        all_mappings[neighborhood] = {}
        
        for folder in folders:
            # Skip if already numeric
            try:
                int(folder)
                print(f"✓ {folder:45} Already numeric (skipping)")
                continue
            except ValueError:
                pass
            
            # Find best match
            deal_id, score, matched_address = find_best_match(folder, csv_mapping, manual_overrides)
            
            if deal_id == "DELETE":
                print(f"🗑 {folder:45} → DELETE (dead folder)")
                all_mappings[neighborhood][folder] = {
                    "deal_id": "DELETE",
                    "score": 1.0,
                    "matched_address": "manual_deletion"
                }
            elif deal_id:
                confidence = "HIGH" if score >= 0.9 else "MEDIUM" if score >= 0.8 else "LOW"
                match_type = matched_address if matched_address in ["exact", "manual_override"] else f"matched: {matched_address}"
                print(f"✓ {folder:45} → {deal_id:6} ({confidence}: {score:.2f}) [{match_type}]")
                all_mappings[neighborhood][folder] = {
                    "deal_id": deal_id,
                    "score": score,
                    "matched_address": matched_address
                }
            else:
                print(f"✗ {folder:45} → NOT FOUND")
                all_mappings[neighborhood][folder] = None
    
    return all_mappings

def delete_s3_folder(neighborhood, folder_name):
    """Delete a folder in S3 by deleting all objects with that prefix"""
    prefix = f'Neighborhood Listing Images/{neighborhood}/{folder_name}/'
    
    # List all objects in folder
    paginator = s3.get_paginator('list_objects_v2')
    objects = []
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            objects.append(obj['Key'])
    
    if not objects:
        print(f"  WARNING: No objects found in {prefix}")
        return False
    
    # Delete all objects
    for key in objects:
        s3.delete_object(Bucket=BUCKET_NAME, Key=key)
        print(f"    Deleted: {key}")
    
    return True

def display_summary(mappings):
    """Display summary of proposed changes"""
    print("\n" + "="*80)
    print("PROPOSED S3 FOLDER RESTRUCTURING SUMMARY")
    print("="*80)
    
    total_rename = 0
    total_delete = 0
    total_missing = 0
    total_low_confidence = 0
    
    for neighborhood, folders in mappings.items():
        for folder, mapping in folders.items():
            if mapping:
                if mapping['deal_id'] == "DELETE":
                    total_delete += 1
                else:
                    total_rename += 1
                    if mapping['score'] < 0.8:
                        total_low_confidence += 1
            else:
                total_missing += 1
    
    print(f"\n  ✓ {total_rename} folders will be renamed to deal IDs")
    print(f"  🗑 {total_delete} folders will be deleted (dead)")
    print(f"  ⚠ {total_low_confidence} folders with low confidence matches (score < 0.8)")
    print(f"  ✗ {total_missing} folders could not be mapped")
    
    if total_missing > 0:
        print(f"\n⚠️  WARNING: {total_missing} folders need manual review")
    
    print("\n" + "="*80)
    
    return total_rename, total_delete, total_missing, total_low_confidence

def execute_restructure(mappings, dry_run=True):
    """Execute the S3 folder restructuring"""
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        print("="*80)
        return
    
    print("\n🚀 EXECUTING RESTRUCTURE")
    print("="*80)
    
    for neighborhood, folders in mappings.items():
        print(f"\nProcessing: {neighborhood}")
        print("-"*80)
        
        for old_name, mapping in folders.items():
            if not mapping:
                continue
            
            # Skip low confidence matches (unless manual override)
            if mapping['score'] < 0.8 and mapping['matched_address'] not in ['manual_override', 'manual_deletion']:
                print(f"⊘ Skipping {old_name} (low confidence: {mapping['score']:.2f})")
                continue
            
            action = mapping['deal_id']
            
            if action == "DELETE":
                print(f"\n🗑 Deleting: {old_name}")
                success = delete_s3_folder(neighborhood, old_name)
                
                if success:
                    print(f"  ✓ Successfully deleted")
                else:
                    print(f"  ✗ Failed to delete")
            else:
                new_name = action
                print(f"\nRenaming: {old_name} → {new_name}")
                success = rename_s3_folder(neighborhood, old_name, new_name)
                
                if success:
                    print(f"  ✓ Successfully renamed to {new_name}")
                else:
                    print(f"  ✗ Failed to rename")

if __name__ == "__main__":
    csv_path = 'attached_assets/deals-2979966-150_1763500957746.csv'
    
    # Manual overrides provided by user
    manual_overrides = {
        "172 Crown Heights, Empire Blvd": "3879",
        "80 5th Ave - 14th St (10th Fl)": "2562",
        "80 5th Ave - 14th St (10th Fl) copy": "2562",
        "150 W25th copy": "2854",
        # Dead folders to delete
        "40-29 235th St, Little Neck": "DELETE",
        "42-23 212th St Bayside,": "DELETE",
        "68 Washington St, Dumbo": "DELETE",
        "85-09 151st Ave, Queens (1)": "DELETE",
    }
    
    print("Step 1: Analyzing S3 folders and matching to CSV...")
    mappings = analyze_and_map(csv_path, manual_overrides)
    
    print("\nStep 2: Generating summary...")
    total_rename, total_delete, total_missing, total_low = display_summary(mappings)
    
    if total_missing > 0:
        print("\n⚠️  WARNING: Some folders still need manual review.")
        print("Please update manual_overrides before executing.")
    else:
        print("\n✅ All folders mapped successfully!")
        print(f"   • {total_rename} folders ready to rename")
        print(f"   • {total_delete} dead folders ready to delete")
        print("\nExecuting restructure...")
        
        # Execute the restructure
        execute_restructure(mappings, dry_run=False)
