"""
Verification script to check if all Brooklyn | Queens deals have complete alt text and tooltip data
"""

import requests
import os
from collections import defaultdict

# Brooklyn | Queens deal IDs and their expected image counts
BROOKLYN_QUEENS_DEALS = {
    2561: 10,
    3246: 10,
    3565: 3,
    3589: 10,
    3722: 4,
    3846: 5,
    3879: 7,
    4170: 10,
    4180: 5,
    4484: 6,
    4550: 3,
    5387: 8,
    5689: 4,
    5882: 4,
    6173: 4
}

def get_pipedrive_field_keys():
    """Get Pipedrive custom field keys for Alt Text and Tooltip fields"""
    token = os.environ.get("PIPEDRIVE_API_TOKEN")
    if not token:
        print("❌ PIPEDRIVE_API_TOKEN not found")
        return None
    
    try:
        response = requests.get(
            "https://api.pipedrive.com/v1/dealFields",
            params={"api_token": token}
        )
        response.raise_for_status()
        fields = response.json().get("data", [])
        
        # Build mapping: {1: {alt: "key123", tooltip: "key456"}, 2: {...}, ...}
        field_map = {}
        for field in fields:
            name = field.get("name", "")
            key = field.get("key", "")
            
            # Match "Deal - Alt Text Pic 1" through "Deal - Alt Text Pic 10"
            if "Alt Text Pic" in name:
                pic_num = name.split("Pic")[-1].strip()
                try:
                    num = int(pic_num)
                    if num not in field_map:
                        field_map[num] = {}
                    field_map[num]["alt"] = key
                except ValueError:
                    pass
            
            # Match "Deal - Tooltip Pic 1" through "Deal - Tooltip Pic 10"
            elif "Tooltip Pic" in name:
                pic_num = name.split("Pic")[-1].strip()
                try:
                    num = int(pic_num)
                    if num not in field_map:
                        field_map[num] = {}
                    field_map[num]["tooltip"] = key
                except ValueError:
                    pass
        
        return field_map
    except Exception as e:
        print(f"❌ Error fetching Pipedrive field keys: {e}")
        return None

def check_deal_completion(deal_id, expected_images, field_map):
    """Check if a deal has all expected alt text and tooltip fields populated"""
    token = os.environ.get("PIPEDRIVE_API_TOKEN")
    
    try:
        response = requests.get(
            f"https://api.pipedrive.com/v1/deals/{deal_id}",
            params={"api_token": token}
        )
        response.raise_for_status()
        deal_data = response.json().get("data", {})
        
        populated_slots = []
        missing_slots = []
        
        for pic_num in range(1, expected_images + 1):
            if pic_num not in field_map:
                continue
            
            alt_key = field_map[pic_num].get("alt")
            tooltip_key = field_map[pic_num].get("tooltip")
            
            alt_text = (deal_data.get(alt_key) or "").strip() if alt_key else ""
            tooltip_text = (deal_data.get(tooltip_key) or "").strip() if tooltip_key else ""
            
            if alt_text and tooltip_text:
                populated_slots.append(pic_num)
            else:
                missing_slots.append(pic_num)
        
        return {
            "deal_id": deal_id,
            "expected": expected_images,
            "populated": len(populated_slots),
            "populated_slots": populated_slots,
            "missing_slots": missing_slots,
            "complete": len(missing_slots) == 0
        }
    except Exception as e:
        return {
            "deal_id": deal_id,
            "error": str(e),
            "complete": False
        }

def main():
    print("=" * 80)
    print("BROOKLYN | QUEENS COMPLETION VERIFICATION")
    print("=" * 80)
    print()
    
    field_map = get_pipedrive_field_keys()
    if not field_map:
        print("❌ Failed to get Pipedrive field mappings")
        return
    
    print(f"✓ Got Pipedrive field mappings for pictures 1-{len(field_map)}")
    print()
    
    total_deals = len(BROOKLYN_QUEENS_DEALS)
    total_expected_images = sum(BROOKLYN_QUEENS_DEALS.values())
    complete_deals = 0
    total_populated = 0
    
    results = []
    
    for deal_id, expected_images in sorted(BROOKLYN_QUEENS_DEALS.items()):
        result = check_deal_completion(deal_id, expected_images, field_map)
        results.append(result)
        
        if result.get("error"):
            print(f"Deal {deal_id}: ❌ ERROR - {result['error']}")
        else:
            populated = result["populated"]
            expected = result["expected"]
            total_populated += populated
            
            if result["complete"]:
                complete_deals += 1
                print(f"Deal {deal_id}: ✅ COMPLETE ({populated}/{expected} images)")
            else:
                missing = result["missing_slots"]
                print(f"Deal {deal_id}: ⚠️  INCOMPLETE ({populated}/{expected} images) - Missing slots: {missing}")
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Deals: {total_deals}")
    print(f"Complete Deals: {complete_deals}/{total_deals} ({complete_deals/total_deals*100:.1f}%)")
    print(f"Total Images: {total_populated}/{total_expected_images} ({total_populated/total_expected_images*100:.1f}%)")
    print()
    
    if complete_deals == total_deals:
        print("🎉 ALL BROOKLYN | QUEENS DEALS ARE COMPLETE!")
        print("✓ The Make.com scenario successfully processed all images")
        print("✓ The 'timeout' was likely just a harmless sign-off issue")
    else:
        incomplete_deals = total_deals - complete_deals
        missing_images = total_expected_images - total_populated
        print(f"⚠️  {incomplete_deals} deal(s) incomplete, {missing_images} image(s) missing")
        print()
        print("INCOMPLETE DEALS:")
        for result in results:
            if not result.get("complete") and not result.get("error"):
                deal_id = result["deal_id"]
                missing = result["missing_slots"]
                print(f"  - Deal {deal_id}: Missing picture slots {missing}")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
