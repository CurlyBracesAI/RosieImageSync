from flask import Blueprint, jsonify
import os
import requests

bp_wix_sync = Blueprint('wix_sync', __name__)

WIX_API_KEY = os.getenv("WIX_ACCESS_KEY_ID")
WIX_SITE_ID = os.getenv("WIX_SITE_ID")
PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN")

WIX_COLLECTION_NAME = "MasterListingsCollection"
WIX_API_BASE = "https://www.wixapis.com/wix-data/v2"
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"


def _get_wix_collection_id():
    """Auto-discover the Wix Collection ID by name"""
    if not WIX_API_KEY or not WIX_SITE_ID:
        return None
    
    try:
        headers = {
            "Authorization": WIX_API_KEY,
            "wix-site-id": WIX_SITE_ID
        }
        response = requests.get(
            f"{WIX_API_BASE}/collections",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        collections = data.get("collections", [])
        for coll in collections:
            if coll.get("displayName") == WIX_COLLECTION_NAME:
                return coll.get("id")
        
        print(f"Collection '{WIX_COLLECTION_NAME}' not found. Available: {[c.get('displayName') for c in collections]}")
        return None
    except Exception as e:
        print(f"Error fetching Wix collection ID: {e}")
        return None


def _fetch_wix_items(collection_id):
    """Fetch all items from Wix collection"""
    if not collection_id or not WIX_API_KEY or not WIX_SITE_ID:
        return []
    
    try:
        headers = {
            "Authorization": WIX_API_KEY,
            "wix-site-id": WIX_SITE_ID
        }
        
        response = requests.get(
            f"{WIX_API_BASE}/collections/{collection_id}/items",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        items = data.get("items", [])
        print(f"✓ Fetched {len(items)} items from Wix collection")
        return items
    except Exception as e:
        print(f"Error fetching Wix items: {e}")
        return []


def _get_pipedrive_field_map():
    """Build field map: human-readable → internal keys"""
    if not PIPEDRIVE_API_TOKEN:
        return None
    
    try:
        response = requests.get(
            f"{PIPEDRIVE_BASE}/dealFields",
            params={"api_token": PIPEDRIVE_API_TOKEN}
        )
        response.raise_for_status()
        fields = response.json().get("data", [])
        
        field_map = {}
        for field in fields:
            name = field.get("name", "")
            key = field.get("key", "")
            field_map[name] = key
        
        return field_map
    except Exception as e:
        print(f"Error fetching Pipedrive field map: {e}")
        return None


def _fetch_pipedrive_deals():
    """Fetch all open deals from Pipedrive"""
    if not PIPEDRIVE_API_TOKEN:
        return []
    
    deals = []
    start = 0
    limit = 500
    
    try:
        while True:
            response = requests.get(
                f"{PIPEDRIVE_BASE}/deals",
                params={
                    "api_token": PIPEDRIVE_API_TOKEN,
                    "start": start,
                    "limit": limit,
                    "status": "open"
                }
            )
            response.raise_for_status()
            data = response.json()
            batch = data.get("data", [])
            
            if not batch:
                break
            
            deals.extend(batch)
            
            pagination = data.get("additional_data", {}).get("pagination", {})
            if not pagination.get("more_items_in_collection"):
                break
            
            start = pagination.get("next_start", 0)
        
        print(f"✓ Fetched {len(deals)} deals from Pipedrive")
        return deals
    except Exception as e:
        print(f"Error fetching Pipedrive deals: {e}")
        return []


def _match_and_link_ids(wix_items, pipedrive_deals, field_map):
    """
    Match Wix items to Pipedrive deals using Pipedrive ID.
    For each Wix item, find its "ID" field (Pipedrive ID) and match to deal.
    Return: list of (wix_item, pipedrive_deal, wix_id) tuples
    """
    matches = []
    
    # Build Pipedrive ID → deal mapping
    pd_id_to_deal = {deal.get("id"): deal for deal in pipedrive_deals}
    
    for wix_item in wix_items:
        wix_item_id = wix_item.get("id")
        item_data = wix_item.get("data", {})
        
        # Wix "ID" field should contain Pipedrive deal ID
        pd_id = item_data.get("ID")
        
        if pd_id and pd_id in pd_id_to_deal:
            pipedrive_deal = pd_id_to_deal[pd_id]
            matches.append({
                "wix_item_id": wix_item_id,
                "pipedrive_deal_id": pd_id,
                "pipedrive_deal": pipedrive_deal
            })
    
    print(f"✓ Matched {len(matches)} Wix items to Pipedrive deals")
    return matches


def _update_pipedrive_with_wix_ids(matches, field_map):
    """
    Update Pipedrive deals with Wix item IDs in the linking field.
    Updates "Deal - Unified Neighborhood Link (Wix ID)" field.
    """
    if not PIPEDRIVE_API_TOKEN or not field_map:
        return 0
    
    wix_id_field_key = field_map.get("Deal - Unified Neighborhood Link (Wix ID)")
    if not wix_id_field_key:
        print("✗ Could not find 'Deal - Unified Neighborhood Link (Wix ID)' field in Pipedrive")
        return 0
    
    updated_count = 0
    
    for match in matches:
        pd_deal_id = match["pipedrive_deal_id"]
        wix_item_id = match["wix_item_id"]
        
        try:
            payload = {
                wix_id_field_key: wix_item_id
            }
            
            response = requests.put(
                f"{PIPEDRIVE_BASE}/deals/{pd_deal_id}",
                params={"api_token": PIPEDRIVE_API_TOKEN},
                json=payload
            )
            response.raise_for_status()
            updated_count += 1
            
        except Exception as e:
            print(f"✗ Error updating deal {pd_deal_id}: {e}")
    
    print(f"✓ Updated {updated_count} Pipedrive deals with Wix item IDs")
    return updated_count


def _build_wix_update_payload(pipedrive_deal, field_map):
    """Convert Pipedrive deal data to Wix item update payload"""
    if not field_map:
        return {}
    
    data = {}
    
    # Map all fields that exist in both systems
    field_mappings = {
        "Deal - ID (Wix)": "ID",
        "Deal - Title": "Title",
        "Deal - Order": "Order",
        "Deal - Neighborhood (primary)": "Neighborhood (primary)",
        "Deal - Neighborhood (secondary)": "Neighborhood (secondary)",
        "Deal - Neighborhood (address details)": "Neighborhood (address details)",
        "Deal - State": "State",
        "Deal - Zip Code": "Zip Code",
        "Deal - Web Description Copy": "Web Description Copy",
        "Deal - Partner Wellspring Weblink": "Partner Wellspring Weblink",
        "Deal - FT | PT Availability/ Requirement": "FT | PT Availability/ Requirement",
        "Deal - Profession | Use": "Profession | Use",
        "Deal - Profession | Use2": "Profession | Use2",
    }
    
    # Add picture + alt/tooltip fields
    for i in range(1, 11):
        field_mappings[f"Deal - Picture {i}"] = f"Picture {i}"
        field_mappings[f"Deal - Alt Text Pic {i}"] = f"Alt Text Pic {i}"
        field_mappings[f"Deal - Tooltip Pic {i}"] = f"Tooltip Pic {i}"
    
    for pd_field, wix_field in field_mappings.items():
        pd_key = field_map.get(pd_field)
        value = pipedrive_deal.get(pd_key) if pd_key else None
        if value:
            data[wix_field] = value
    
    return data


def _sync_data_to_wix(collection_id, matches, field_map):
    """Bulk sync all Pipedrive data to Wix items"""
    if not collection_id or not WIX_API_KEY or not WIX_SITE_ID or not matches:
        return {"error": "Missing collection_id, credentials, or matches"}
    
    try:
        wix_items = []
        
        for match in matches:
            wix_item_id = match["wix_item_id"]
            pipedrive_deal = match["pipedrive_deal"]
            
            item_data = _build_wix_update_payload(pipedrive_deal, field_map)
            
            wix_items.append({
                "dataItemId": wix_item_id,
                "data": item_data
            })
        
        headers = {
            "Authorization": WIX_API_KEY,
            "wix-site-id": WIX_SITE_ID,
            "Content-Type": "application/json"
        }
        
        payload = {"items": wix_items}
        
        response = requests.post(
            f"{WIX_API_BASE}/collections/{collection_id}/items/bulk/save",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        
        print(f"✓ Synced {len(wix_items)} items to Wix")
        return response.json()
        
    except Exception as e:
        print(f"✗ Error syncing to Wix: {e}")
        return {"error": str(e)}


@bp_wix_sync.route('/sync-wix', methods=['POST', 'GET'])
def sync_wix():
    """
    Master sync endpoint: 
    1. Fetch Wix items and Pipedrive deals
    2. Match by Pipedrive ID
    3. Update Pipedrive with Wix item IDs
    4. Sync all data to Wix
    """
    if not all([WIX_API_KEY, WIX_SITE_ID, PIPEDRIVE_API_TOKEN]):
        return jsonify({
            "error": "Missing credentials",
            "details": {
                "wix_api_key": bool(WIX_API_KEY),
                "wix_site_id": bool(WIX_SITE_ID),
                "pipedrive_token": bool(PIPEDRIVE_API_TOKEN)
            }
        }), 500
    
    # Get Wix collection ID
    collection_id = _get_wix_collection_id()
    if not collection_id:
        return jsonify({"error": f"Could not find Wix collection '{WIX_COLLECTION_NAME}'"}), 500
    
    print(f"✓ Found Wix Collection: {collection_id}")
    
    # Get field mapping
    field_map = _get_pipedrive_field_map()
    if not field_map:
        return jsonify({"error": "Could not fetch Pipedrive field map"}), 500
    
    print(f"✓ Built Pipedrive field map")
    
    # Fetch Wix items and Pipedrive deals
    wix_items = _fetch_wix_items(collection_id)
    pipedrive_deals = _fetch_pipedrive_deals()
    
    if not wix_items or not pipedrive_deals:
        return jsonify({
            "error": "No Wix items or Pipedrive deals found",
            "wix_items_count": len(wix_items),
            "pipedrive_deals_count": len(pipedrive_deals)
        }), 400
    
    # Match and link IDs
    matches = _match_and_link_ids(wix_items, pipedrive_deals, field_map)
    
    if not matches:
        return jsonify({
            "message": "No matches found between Wix items and Pipedrive deals",
            "wix_items_count": len(wix_items),
            "pipedrive_deals_count": len(pipedrive_deals),
            "matches_count": 0
        }), 200
    
    # Update Pipedrive with Wix item IDs
    updated_count = _update_pipedrive_with_wix_ids(matches, field_map)
    
    # Sync data to Wix
    wix_response = _sync_data_to_wix(collection_id, matches, field_map)
    
    return jsonify({
        "status": "success",
        "wix_items_fetched": len(wix_items),
        "pipedrive_deals_fetched": len(pipedrive_deals),
        "matches_found": len(matches),
        "pipedrive_updated": updated_count,
        "wix_sync_response": wix_response
    }), 200
