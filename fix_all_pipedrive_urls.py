"""
Fix all Pipedrive URLs to use corrected S3 folder names with underscores instead of pipes
This handles all 5 neighborhoods: Brooklyn | Queens, Midtown East, West Village, Upper West Side, Upper East Side
"""

import requests
import os
from urllib.parse import quote

PIPEDRIVE_API_TOKEN = os.environ.get('PIPEDRIVE_API_TOKEN')
PIPEDRIVE_API_URL = 'https://api.pipedrive.com/v1'

# Mapping of old folder names (as they appear in URLs) to new folder names
FOLDER_NAME_MAP = {
    # Old format (with pipes/spaces) -> New format (with underscores)
    'Brooklyn | Queens AWS S3': 'Brooklyn_Queens_AWS_S3',
    'Midtown East | Gr Cent AWS S3': 'Midtown_East_Gr_Cent_AWS_S3',
    'UnSQ | Gren\'Villl. AWS S3': 'UnSQ_Gren_Villl_AWS_S3',
    "UnSQ | Gren'Villl. AWS S3": 'UnSQ_Gren_Villl_AWS_S3',  # Alternative format
    'Upper West Side AWS S3': 'Upper_West_Side_AWS_S3',
    'Upper East Side AWS S3': 'UES',  # Assume this is the old name
}

def get_picture_field_keys():
    """Fetch the custom field keys for Picture 1-10 from Pipedrive"""
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
        print(f'❌ Error fetching Pipedrive field keys: {e}')
        return {}

def fix_url(old_url):
    """Convert old URL format to new URL format with corrected S3 folder names"""
    if not old_url:
        return None
    
    for old_folder, new_folder in FOLDER_NAME_MAP.items():
        # URL-encoded version of old folder name
        encoded_old = quote(old_folder, safe='')
        
        if encoded_old in old_url:
            # Replace the encoded old folder name with new folder name
            new_url = old_url.replace(encoded_old, new_folder)
            return new_url
    
    # If no mapping found, return None to indicate it couldn't be fixed
    return None

def get_all_deals():
    """Get all deals from Pipedrive with pagination"""
    all_deals = []
    start = 0
    
    while True:
        try:
            response = requests.get(
                f'{PIPEDRIVE_API_URL}/deals',
                params={
                    'api_token': PIPEDRIVE_API_TOKEN,
                    'start': start,
                    'limit': 500
                }
            )
            response.raise_for_status()
            data = response.json().get('data', [])
            
            if not data:
                break
            
            all_deals.extend(data)
            
            # Check if there are more deals
            if not response.json().get('additional_data', {}).get('pagination', {}).get('more_items_in_collection'):
                break
            
            start += 500
        except Exception as e:
            print(f'❌ Error fetching deals: {e}')
            break
    
    return all_deals

def update_deal_picture_url(deal_id, picture_num, new_url, picture_fields):
    """Update a specific picture URL in Pipedrive"""
    if picture_num not in picture_fields:
        return False
    
    field_key = picture_fields[picture_num]
    
    try:
        response = requests.put(
            f'{PIPEDRIVE_API_URL}/deals/{deal_id}',
            params={'api_token': PIPEDRIVE_API_TOKEN},
            json={field_key: new_url}
        )
        response.raise_for_status()
        return response.json().get('success', False)
    except Exception as e:
        print(f'  ⚠️ Error updating deal {deal_id}, picture {picture_num}: {e}')
        return False

def main():
    print('=' * 80)
    print('PIPEDRIVE URL FIX - ALL NEIGHBORHOODS')
    print('=' * 80)
    print()
    
    picture_fields = get_picture_field_keys()
    if not picture_fields:
        print('❌ Failed to get picture field keys')
        return
    
    print(f'✓ Got picture field keys for pictures 1-{len(picture_fields)}')
    print()
    
    all_deals = get_all_deals()
    print(f'✓ Retrieved {len(all_deals)} total deals from Pipedrive')
    print()
    
    stats = {
        'total_deals': len(all_deals),
        'deals_with_updates': 0,
        'urls_fixed': 0,
        'urls_failed': 0,
        'urls_unchanged': 0,
    }
    
    for deal in all_deals:
        deal_id = deal.get('id')
        updated_any = False
        
        for pic_num in range(1, 11):
            if pic_num not in picture_fields:
                continue
            
            old_url = deal.get(picture_fields[pic_num])
            
            if not old_url:
                continue
            
            new_url = fix_url(old_url)
            
            if new_url is None:
                stats['urls_unchanged'] += 1
                continue
            
            if new_url == old_url:
                stats['urls_unchanged'] += 1
                continue
            
            # Update in Pipedrive
            if update_deal_picture_url(deal_id, pic_num, new_url, picture_fields):
                stats['urls_fixed'] += 1
                print(f'✓ Deal {deal_id}, Picture {pic_num}: URL fixed')
                updated_any = True
            else:
                stats['urls_failed'] += 1
                print(f'❌ Deal {deal_id}, Picture {pic_num}: Failed to update')
        
        if updated_any:
            stats['deals_with_updates'] += 1
    
    print()
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'Total Deals Processed: {stats["total_deals"]}')
    print(f'Deals with Updates: {stats["deals_with_updates"]}')
    print(f'URLs Fixed: {stats["urls_fixed"]}')
    print(f'URLs Failed: {stats["urls_failed"]}')
    print(f'URLs Unchanged: {stats["urls_unchanged"]}')
    print()
    
    if stats['urls_fixed'] > 0:
        print('🎉 Successfully fixed all URL issues!')
        print('✓ All Pipedrive deals now point to correct S3 folder names')
    else:
        print('⚠️ No URLs needed fixing or all URLs already correct')
    
    print('=' * 80)

if __name__ == '__main__':
    main()
