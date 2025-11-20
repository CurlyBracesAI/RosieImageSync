import boto3
import requests
import os
from urllib.parse import quote

s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

PIPEDRIVE_API_TOKEN = os.environ.get('PIPEDRIVE_API_TOKEN')
PIPEDRIVE_API_URL = 'https://api.pipedrive.com/v1'
BUCKET = 'neighborhood-listing-images'
NEIGHBORHOOD_PREFIX = 'Neighborhood Listing Images/Brooklyn | Queens AWS S3/'

def get_pipedrive_picture_field_keys():
    """Fetch the custom field keys for Picture 1-10 from Pipedrive"""
    try:
        response = requests.get(
            f'{PIPEDRIVE_API_URL}/dealFields',
            params={'api_token': PIPEDRIVE_API_TOKEN}
        )
        response.raise_for_status()
        fields = response.json().get('data', [])
        
        # Build mapping: {1: 'field_key_abc', 2: 'field_key_def', ...}
        picture_fields = {}
        for field in fields:
            name = field.get('name', '')
            key = field.get('key', '')
            
            # Match "Picture 1" through "Picture 10" (exact format from Pipedrive)
            if name.startswith('Picture '):
                try:
                    pic_num = int(name.replace('Picture ', '').strip())
                    if 1 <= pic_num <= 10:
                        picture_fields[pic_num] = key
                except ValueError:
                    pass
        
        return picture_fields
    except Exception as e:
        print(f'Error fetching Pipedrive field keys: {e}')
        return {}

def get_s3_inventory():
    """Get all images from Brooklyn | Queens AWS S3 folder"""
    deals_inventory = {}
    
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=NEIGHBORHOOD_PREFIX, Delimiter='/')
    
    if 'CommonPrefixes' not in response:
        return deals_inventory
    
    for cp in response['CommonPrefixes']:
        deal_id = cp['Prefix'].rstrip('/').split('/')[-1]
        
        # Get files in this deal folder
        files_response = s3.list_objects_v2(Bucket=BUCKET, Prefix=cp['Prefix'])
        
        images = {}
        if 'Contents' in files_response:
            for obj in files_response['Contents']:
                key = obj['Key']
                if key.endswith('/'):
                    continue
                
                filename = key.split('/')[-1]
                
                # Skip .DS_Store files
                if filename == '.DS_Store':
                    continue
                
                # Extract picture number from filename (1.jpg -> 1, 2.png -> 2)
                base_name = filename.split('.')[0]
                if base_name.isdigit():
                    pic_num = int(base_name)
                    if 1 <= pic_num <= 10:
                        # Generate public S3 URL with proper encoding (preserve slashes)
                        url = f'https://{BUCKET}.s3.amazonaws.com/{quote(key, safe="/")}'
                        images[pic_num] = url
        
        if images:
            deals_inventory[deal_id] = images
    
    return deals_inventory

def update_pipedrive_deal(deal_id, images_dict, field_keys):
    """Update Pipedrive deal with new image URLs
    
    Args:
        deal_id: Pipedrive deal ID
        images_dict: {1: 'url1', 2: 'url2', ...}
        field_keys: {1: 'field_key_abc', 2: 'field_key_def', ...}
    """
    # Build update payload using correct field keys
    payload = {}
    
    for pic_num, url in images_dict.items():
        if pic_num in field_keys:
            field_key = field_keys[pic_num]
            payload[field_key] = url
        else:
            print(f'  Warning: No field key found for Picture {pic_num}')
    
    if not payload:
        return False, 'No valid fields to update'
    
    # Send update to Pipedrive
    url = f'{PIPEDRIVE_API_URL}/deals/{deal_id}'
    params = {'api_token': PIPEDRIVE_API_TOKEN}
    
    try:
        response = requests.put(url, params=params, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            return True, 'Updated successfully'
        else:
            return False, data.get('error', 'Unknown error')
    except Exception as e:
        return False, str(e)

if __name__ == '__main__':
    print('Pipedrive URL Update Script')
    print('Updating Brooklyn | Queens AWS S3 image URLs')
    print('='*60)
    print()
    
    print('Step 1: Fetching Pipedrive field keys...')
    field_keys = get_pipedrive_picture_field_keys()
    if not field_keys:
        print('✗ Failed to fetch field keys from Pipedrive')
        exit(1)
    print(f'✓ Found field keys for {len(field_keys)} picture slots')
    print()
    
    print('Step 2: Getting S3 inventory...')
    inventory = get_s3_inventory()
    print(f'✓ Found {len(inventory)} deals with images')
    print()
    
    # Show preview
    print('Preview of URLs to upload:')
    for deal_id in sorted(inventory.keys())[:3]:
        images = inventory[deal_id]
        print(f'  Deal {deal_id}: {len(images)} pictures')
        for pic_num in sorted(images.keys())[:2]:
            url = images[pic_num]
            short_url = url.split('/')[-1]
            print(f'    Picture {pic_num}: .../{short_url}')
    print()
    
    # Ask for confirmation
    print('Step 3: Update Pipedrive')
    print(f'This will update {len(inventory)} deals')
    print()
    
    response = input('Proceed with update? (yes/no): ')
    if response.lower() != 'yes':
        print('Aborted.')
        exit(0)
    
    print()
    print('Updating Pipedrive deals...')
    print('-'*60)
    
    success_count = 0
    error_count = 0
    
    for deal_id in sorted(inventory.keys()):
        images = inventory[deal_id]
        success, message = update_pipedrive_deal(deal_id, images, field_keys)
        
        if success:
            print(f'✓ Deal {deal_id}: Updated {len(images)} pictures')
            success_count += 1
        else:
            print(f'✗ Deal {deal_id}: {message}')
            error_count += 1
    
    print('-'*60)
    print(f'Complete! {success_count} successful, {error_count} errors')
