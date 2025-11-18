import boto3
import os
import csv
from collections import defaultdict
from urllib.parse import urlparse

s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

BUCKET = 'neighborhood-listing-images'
BASE_PREFIX = 'Neighborhood Listing Images/'
CSV_PATH = './attached_assets/deals-2979966-150_1763500957746.csv'

NEIGHBORHOODS = [
    'UnSQ:Gren\'Villl.',
    'Brooklyn | Queens'
]

def parse_csv_image_mapping():
    """Parse CSV to get image filename → deal ID mapping"""
    filename_to_deals = defaultdict(list)  # filename → list of (deal_id, picture_num, neighborhood)
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            deal_id = row.get('Deal - ID')
            if not deal_id:
                continue
            
            # Get neighborhood from the row
            neighborhood = row.get('Deal - Neighborhood (primary)', '')
            
            # Parse each picture URL (1-10)
            for pic_num in range(1, 11):
                pic_key = f'Deal - Picture {pic_num}'
                url = row.get(pic_key, '').strip()
                
                if url:
                    # Extract filename from URL
                    parsed = urlparse(url)
                    path = parsed.path
                    filename = path.split('/')[-1] if '/' in path else url
                    
                    # Store mapping
                    filename_to_deals[filename].append({
                        'deal_id': deal_id,
                        'picture_num': pic_num,
                        'neighborhood': neighborhood,
                        'url': url
                    })
    
    return filename_to_deals

def get_current_s3_inventory():
    """Get current S3 file inventory for neighborhoods"""
    inventory = []  # List of {current_key, filename, current_deal_id, current_neighborhood}
    
    for neighborhood in NEIGHBORHOODS:
        prefix = f"{BASE_PREFIX}{neighborhood}/"
        
        # List all deal folders
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, Delimiter='/')
        
        if 'CommonPrefixes' not in response:
            continue
        
        for cp in response['CommonPrefixes']:
            deal_id = cp['Prefix'].rstrip('/').split('/')[-1]
            
            # List files in this deal folder
            files_response = s3.list_objects_v2(Bucket=BUCKET, Prefix=cp['Prefix'])
            
            if 'Contents' in files_response:
                for obj in files_response['Contents']:
                    key = obj['Key']
                    if key.endswith('/'):  # Skip folder markers
                        continue
                    
                    filename = key.split('/')[-1]
                    
                    inventory.append({
                        'current_key': key,
                        'filename': filename,
                        'current_deal_id': deal_id,
                        'current_neighborhood': neighborhood
                    })
    
    return inventory

def create_redistribution_plan(csv_mapping, s3_inventory):
    """Create plan to move files from current location to correct location"""
    moves = []  # List of {source_key, dest_key, filename, from_deal, to_deal, reason}
    unmatched_files = []  # Files in S3 but not in CSV
    missing_files = []  # Files in CSV but not in S3
    
    # Create lookup: filename → current S3 location
    filename_to_s3 = {}
    for item in s3_inventory:
        filename = item['filename']
        if filename not in filename_to_s3:
            filename_to_s3[filename] = []
        filename_to_s3[filename].append(item)
    
    # For each file in CSV, check if it's in the correct deal folder
    for filename, deal_entries in csv_mapping.items():
        if filename not in filename_to_s3:
            # File should exist but doesn't
            for entry in deal_entries:
                missing_files.append({
                    'filename': filename,
                    'expected_deal_id': entry['deal_id'],
                    'picture_num': entry['picture_num']
                })
            continue
        
        # File exists in S3 - check if it's in the right place
        s3_locations = filename_to_s3[filename]
        
        # Expected location (use first CSV entry as canonical)
        expected_entry = deal_entries[0]
        expected_deal_id = expected_entry['deal_id']
        expected_neighborhood = map_neighborhood(expected_entry['neighborhood'])
        
        # Skip if neighborhood is not in our scope (other neighborhoods we're not processing)
        if expected_neighborhood is None:
            continue
        
        # Check current location
        for s3_item in s3_locations:
            current_deal_id = s3_item['current_deal_id']
            current_neighborhood = s3_item['current_neighborhood']
            
            # If file is not in the correct deal folder, plan to move it
            if current_deal_id != expected_deal_id or current_neighborhood != expected_neighborhood:
                dest_key = f"{BASE_PREFIX}{expected_neighborhood}/{expected_deal_id}/{filename}"
                
                moves.append({
                    'source_key': s3_item['current_key'],
                    'dest_key': dest_key,
                    'filename': filename,
                    'from_deal': current_deal_id,
                    'to_deal': expected_deal_id,
                    'from_neighborhood': current_neighborhood,
                    'to_neighborhood': expected_neighborhood,
                    'reason': 'Incorrect folder'
                })
    
    # Find files in S3 that aren't in CSV (orphans)
    for filename, s3_locations in filename_to_s3.items():
        if filename not in csv_mapping:
            for s3_item in s3_locations:
                unmatched_files.append({
                    'filename': filename,
                    'current_key': s3_item['current_key'],
                    'current_deal_id': s3_item['current_deal_id']
                })
    
    return moves, unmatched_files, missing_files

def map_neighborhood(csv_neighborhood):
    """Map CSV neighborhood names to S3 folder names"""
    # West Village folder contains multiple CSV neighborhoods
    west_village_neighborhoods = [
        'West Vill./Union Sq',
        'Gramercy/Flatiron',
        'Chelsea/Penn'
    ]
    
    # Brooklyn | Queens folder
    brooklyn_neighborhoods = [
        'Brooklyn',
        'Queens',
        'Brooklyn | Queens'
    ]
    
    # Check West Village variations
    for neighborhood in west_village_neighborhoods:
        if neighborhood in csv_neighborhood:
            return 'UnSQ:Gren\'Villl.'
    
    # Check Brooklyn variations
    for neighborhood in brooklyn_neighborhoods:
        if neighborhood in csv_neighborhood:
            return 'Brooklyn | Queens'
    
    # Return None for neighborhoods we're not processing
    return None

def execute_redistribution(moves, dry_run=True):
    """Execute the file moves"""
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - No changes will be made")
        print("="*60)
    
    for idx, move in enumerate(moves, 1):
        print(f"\n{idx}. {move['filename']}")
        print(f"   FROM: {move['from_neighborhood']}/{move['from_deal']}")
        print(f"   TO:   {move['to_neighborhood']}/{move['to_deal']}")
        
        if not dry_run:
            try:
                # Copy to new location
                s3.copy_object(
                    Bucket=BUCKET,
                    CopySource={'Bucket': BUCKET, 'Key': move['source_key']},
                    Key=move['dest_key']
                )
                
                # Delete from old location
                s3.delete_object(Bucket=BUCKET, Key=move['source_key'])
                
                print(f"   ✓ Moved successfully")
            except Exception as e:
                print(f"   ✗ Error: {e}")

if __name__ == '__main__':
    print("S3 Image Redistribution Script")
    print("Using CSV as source of truth to fix folder pooling\n")
    
    print("Step 1: Parsing CSV to get correct image mapping...")
    csv_mapping = parse_csv_image_mapping()
    print(f"✓ Found {len(csv_mapping)} unique image filenames in CSV")
    
    print("\nStep 2: Getting current S3 inventory...")
    s3_inventory = get_current_s3_inventory()
    print(f"✓ Found {len(s3_inventory)} files in S3")
    
    print("\nStep 3: Creating redistribution plan...")
    moves, unmatched, missing = create_redistribution_plan(csv_mapping, s3_inventory)
    
    print(f"\n✓ Redistribution Plan:")
    print(f"  - Files to move: {len(moves)}")
    print(f"  - Unmatched files (in S3, not in CSV): {len(unmatched)}")
    print(f"  - Missing files (in CSV, not in S3): {len(missing)}")
    
    if unmatched:
        print(f"\n⚠️ Unmatched files (will be left in place):")
        for item in unmatched[:10]:
            print(f"  - {item['filename']} (in deal {item['current_deal_id']})")
        if len(unmatched) > 10:
            print(f"  ... and {len(unmatched) - 10} more")
    
    if missing:
        print(f"\n⚠️ Missing files (expected but not found):")
        for item in missing[:10]:
            print(f"  - {item['filename']} (expected in deal {item['expected_deal_id']})")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    
    if moves:
        print("\n" + "="*60)
        print("EXECUTING MOVES (DRY RUN)")
        print("="*60)
        execute_redistribution(moves, dry_run=True)
        
        print("\n\n" + "="*60)
        print("DRY RUN COMPLETE")
        print("="*60)
        print("\nTo execute for real, run with dry_run=False")
    else:
        print("\n✓ No moves needed - all files are in correct locations!")
