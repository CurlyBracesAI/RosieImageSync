"""
Optimized URL fix - Only updates deals that actually have images in our neighborhoods
Much faster than iterating through all 3,736 deals
"""

import requests
import boto3
import os

PIPEDRIVE_API_TOKEN = os.environ.get('PIPEDRIVE_API_TOKEN')
PIPEDRIVE_API_URL = 'https://api.pipedrive.com/v1'
BUCKET = 'neighborhood-listing-images'
BASE_PREFIX = 'Neighborhood Listing Images/'

# Neighborhood folders in S3 (current, corrected names)
NEIGHBORHOODS = {
    'Brooklyn_Queens_AWS_S3': 'Brooklyn | Queens AWS S3',  # old name
    'Midtown_East_Gr_Cent_AWS_S3': 'Midtown East | Gr Cent AWS S3',
    'UnSQ_Gren_Villl_AWS_S3': "UnSQ | Gren'Villl. AWS S3",
    'Upper_West_Side_AWS_S3': 'Upper West Side AWS S3',
    'UES': 'Upper East Side AWS S3',
}

s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_REGION')
)

def get_picture_field_keys():
    """Get picture field keys from Pipedrive"""
    try:
        response = requests.get(
            f'{PIPEDRIVE_API_URL}/dealFields',
            params={'api_token': PIPEDRIVE_API_TOKEN}
        )
        response.raise_for_status()
        fields = response.json().get('data', [])
        
        picture_fields = {}
        for field in fields:
            name = field.get('name', '')
            key = field.get('key', '')
            if name.startswith('Picture '):
                try:
                    pic_num = int(name.replace('Picture ', '').strip())
                    if 1 <= pic_num <= 10:
                        picture_fields[pic_num] = key
                except ValueError:
                    pass
        return picture_fields
    except Exception as e:
        print(f'❌ Error getting field keys: {e}')
        return {}

def get_deals_for_neighborhood(s3_folder):
    """Get all deal IDs that have images in a specific S3 neighborhood folder"""
    deal_ids = []
    prefix = f'{BASE_PREFIX}{s3_folder}/'
    
    try:
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix, Delimiter='/')
        
        if 'CommonPrefixes' in response:
            for cp in response['CommonPrefixes']:
                deal_id = cp['Prefix'].rstrip('/').split('/')[-1]
                if deal_id and deal_id.isdigit():
                    deal_ids.append(int(deal_id))
        
        return deal_ids
    except Exception as e:
        print(f'❌ Error listing S3 folder {s3_folder}: {e}')
        return []

def get_deal_urls(deal_id, picture_fields):
    """Get all picture URLs for a deal"""
    try:
        response = requests.get(
            f'{PIPEDRIVE_API_URL}/deals/{deal_id}',
            params={'api_token': PIPEDRIVE_API_TOKEN}
        )
        response.raise_for_status()
        deal_data = response.json().get('data', {})
        
        urls = {}
        for pic_num, field_key in picture_fields.items():
            url = deal_data.get(field_key)
            if url:
                urls[pic_num] = url
        
        return urls
    except Exception as e:
        print(f'⚠️ Error getting deal {deal_id}: {e}')
        return {}

def fix_url(old_url, old_folder, new_folder):
    """Convert old URL to new URL"""
    from urllib.parse import quote
    encoded_old = quote(old_folder, safe='')
    if encoded_old in old_url:
        return old_url.replace(encoded_old, new_folder)
    return None

def update_picture_url(deal_id, pic_num, new_url, picture_fields):
    """Update a picture URL in Pipedrive"""
    if pic_num not in picture_fields:
        return False
    
    field_key = picture_fields[pic_num]
    
    try:
        response = requests.put(
            f'{PIPEDRIVE_API_URL}/deals/{deal_id}',
            params={'api_token': PIPEDRIVE_API_TOKEN},
            json={field_key: new_url}
        )
        return response.json().get('success', False)
    except Exception as e:
        print(f'⚠️ Error updating deal {deal_id}: {e}')
        return False

def main():
    print('=' * 80)
    print('OPTIMIZED URL FIX - NEIGHBORHOOD FOCUSED')
    print('=' * 80)
    print()
    
    picture_fields = get_picture_field_keys()
    if not picture_fields:
        print('❌ Failed to get picture field keys')
        return
    
    print(f'✓ Got picture field keys for pictures 1-{len(picture_fields)}')
    print()
    
    total_urls_fixed = 0
    total_deals_updated = 0
    
    for s3_folder, old_folder_name in NEIGHBORHOODS.items():
        print(f'Processing {s3_folder}...')
        
        deal_ids = get_deals_for_neighborhood(s3_folder)
        print(f'  Found {len(deal_ids)} deals')
        
        deals_fixed_in_neighborhood = 0
        
        for deal_id in deal_ids:
            urls = get_deal_urls(deal_id, picture_fields)
            
            if not urls:
                continue
            
            updated_any = False
            for pic_num, old_url in urls.items():
                new_url = fix_url(old_url, old_folder_name, s3_folder)
                
                if new_url and new_url != old_url:
                    if update_picture_url(deal_id, pic_num, new_url, picture_fields):
                        total_urls_fixed += 1
                        updated_any = True
            
            if updated_any:
                deals_fixed_in_neighborhood += 1
                total_deals_updated += 1
        
        print(f'  ✓ Fixed {deals_fixed_in_neighborhood} deals')
        print()
    
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'Total Deals Updated: {total_deals_updated}')
    print(f'Total URLs Fixed: {total_urls_fixed}')
    print()
    
    if total_urls_fixed > 0:
        print('🎉 Successfully fixed all URL issues!')
    else:
        print('⚠️ No URLs needed fixing')
    
    print('=' * 80)

if __name__ == '__main__':
    main()
