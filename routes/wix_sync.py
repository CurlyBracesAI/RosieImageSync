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
    """Fetch all open deals from Pipedrive with Wix ID"""
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
        
        return deals
    except Exception as e:
        print(f"Error fetching Pipedrive deals: {e}")
        return []


def _build_wix_items(deals, field_map):
    """Convert Pipedrive deals to Wix items"""
    if not field_map:
        return []
    
    wix_items = []
    
    for deal in deals:
        deal_id = deal.get("id")
        
        # Get Wix ID from "Deal - Unified Neighborhood Link (Wix ID)" field
        wix_id_key = field_map.get("Deal - Unified Neighborhood Link (Wix ID)")
        wix_item_id = deal.get(wix_id_key) if wix_id_key else None
        
        if not wix_item_id:
            continue
        
        # Build data payload for Wix
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
            value = deal.get(pd_key) if pd_key else None
            if value:
                data[wix_field] = value
        
        wix_items.append({
            "dataItemId": wix_item_id,
            "data": data
        })
    
    return wix_items


def _sync_to_wix(collection_id, wix_items):
    """Bulk upload items to Wix"""
    if not collection_id or not wix_items or not WIX_API_KEY or not WIX_SITE_ID:
        return {"error": "Missing collection_id, items, or credentials"}
    
    try:
        headers = {
            "Authorization": WIX_API_KEY,
            "wix-site-id": WIX_SITE_ID,
            "Content-Type": "application/json"
        }
        
        payload = {
            "items": wix_items
        }
        
        response = requests.post(
            f"{WIX_API_BASE}/collections/{collection_id}/items/bulk/save",
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error syncing to Wix: {e}")
        return {"error": str(e)}


@bp_wix_sync.route('/sync-wix', methods=['POST', 'GET'])
def sync_wix():
    """
    Master sync endpoint: fetch Pipedrive deals → build Wix items → bulk save to Wix
    """
    # Validate credentials
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
    
    # Fetch Pipedrive deals
    deals = _fetch_pipedrive_deals()
    print(f"✓ Fetched {len(deals)} deals from Pipedrive")
    
    # Build Wix items
    wix_items = _build_wix_items(deals, field_map)
    print(f"✓ Built {len(wix_items)} Wix items")
    
    if not wix_items:
        return jsonify({
            "message": "No deals with Wix IDs found",
            "deals_fetched": len(deals),
            "items_built": 0
        }), 200
    
    # Sync to Wix
    wix_response = _sync_to_wix(collection_id, wix_items)
    
    return jsonify({
        "status": "success",
        "deals_fetched": len(deals),
        "items_built": len(wix_items),
        "wix_response": wix_response
    }), 200
