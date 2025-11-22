from flask import Blueprint, jsonify, request
import os
import requests

bp_wix_sync = Blueprint('wix_sync', __name__)

WIX_API_KEY = os.getenv("WIX_ACCESS_KEY_ID")
WIX_SITE_ID = os.getenv("WIX_SITE_ID")
PIPEDRIVE_API_TOKEN = os.getenv("PIPEDRIVE_API_TOKEN")

WIX_COLLECTION_ID = "Import455"  # The actual collection ID (display name is "MasterListingsCollection")
WIX_API_BASE = "https://www.wixapis.com/wix-data/v2"
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"




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


def _fetch_pipedrive_deals_filtered(filter_id, limit=500):
    """Fetch deals using filter endpoint - returns ALL custom fields automatically"""
    if not PIPEDRIVE_API_TOKEN:
        return []
    
    try:
        url = f"{PIPEDRIVE_BASE}/deals"
        params = {
            "api_token": PIPEDRIVE_API_TOKEN,
            "filter_id": filter_id,
            "limit": limit,
            "start": 0
        }
        headers = {"Accept": "application/json"}
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        deals = response.json().get("data") or []
        print(f"✓ Fetched {len(deals)} deals from Pipedrive using filter {filter_id}")
        return deals
    except Exception as e:
        print(f"Error fetching Pipedrive deals with filter: {e}")
        return []


def _build_wix_item(deal, field_map):
    """
    Convert a Pipedrive deal into a Wix-compliant item payload.
    Uses field_map to map custom field display names to their internal Pipedrive keys.
    Returns item WITHOUT {"data": {...}} wrapper - Wix API expects items directly.
    """
    if not field_map:
        return {}
    
    # Map display names to Wix field keys
    field_mappings = {
        # Basic fields
        "Title": "title",
        "Neighborhood (primary)": "dealNeighborhoodPrimary",
        "Neighborhood (address details)": "dealNeighborhoodAddressDetails",
        "State": "dealState",
        "Zip Code": "dealZipCode",
        "Map": "dealMap",
        "Slug Address": "dealSlugAddress",
        "Stage": "dealStage",
        "Web Description Copy": "dealWebDescriptionCopy",
        "Partner Wellspring Weblink": "dealOwr",
        "FT | PT Availability/ Requirement": "dealFTPT",
        "Profession | Use": "dealProfessionUse",
        "Profession | Use2": "dealProfessionUse2",
        "Unified Neighborhood Link": "unifiedNeighborhoodLink",
        "Neighborhood Link Local": "neighborhoodLinkLocal",
    }
    
    # Add picture + alt/tooltip fields (1-10)
    for i in range(1, 11):
        field_mappings[f"Picture {i}"] = f"dealPicture{i}"
        field_mappings[f"Alt Text Pic {i}"] = f"dealAltTextPic{i}"
        field_mappings[f"Tooltip Pic {i}"] = f"dealTooltipPic{i}"
    
    # Build item, using field_map to lookup custom field keys
    item = {
        "_id": str(deal.get("id")),  # Use numeric Pipedrive ID as Wix _id
    }
    
    for display_name, wix_key in field_mappings.items():
        # Get the internal Pipedrive key for this display name
        pd_internal_key = field_map.get(display_name)
        if pd_internal_key:
            value = deal.get(pd_internal_key)
            if value is not None and value != "":
                item[wix_key] = value
    
    return item  # Return item directly, no {"data": {...}} wrapper


def _sync_to_wix(collection_id, pipedrive_deals, field_map):
    """
    Sync Pipedrive deals to Wix using the bulk save endpoint.
    Correct structure per Wix REST API:
    - dataCollectionId: collection ID (e.g., "Import455")
    - dataItems: array of {_id, data} objects
    """
    if not collection_id or not WIX_API_KEY or not WIX_SITE_ID or not pipedrive_deals:
        return {"error": "Missing collection_id, credentials, or deals"}
    
    try:
        data_items = []
        
        for deal in pipedrive_deals:
            # Build Wix item data
            item_data = _build_wix_item(deal, field_map)
            # Wrap in Wix data structure
            data_items.append({
                "_id": item_data.pop("_id"),  # Extract _id
                "data": item_data  # Remaining fields go in data
            })
        
        headers = {
            "Authorization": f"Bearer {WIX_API_KEY}",
            "wix-site-id": WIX_SITE_ID,
            "Content-Type": "application/json"
        }
        
        # Correct Wix REST API payload structure
        payload = {
            "dataCollectionId": collection_id,
            "dataItems": data_items
        }
        
        print(f"Syncing {len(data_items)} items to Wix collection '{collection_id}'...")
        if len(data_items) > 0:
            print(f"Sample item fields: {list(data_items[0]['data'].keys())}")
        
        bulk_endpoint = f"{WIX_API_BASE}/bulk/items/save"
        print(f"Wix endpoint: {bulk_endpoint}")
        
        print("\n=== DEBUG: FINAL WIX PAYLOAD ===")
        import json
        print(json.dumps(payload, indent=2)[:4000])  # Trim so Replit doesn't choke
        
        print("\n=== DEBUG: FIRST ITEM ===")
        print(json.dumps(data_items[0], indent=2))
        
        response = requests.post(
            bulk_endpoint,
            headers=headers,
            json=payload
        )
        
        print("\n=== DEBUG: WIX RESPONSE ===")
        print(response.status_code)
        print(response.text)
        
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Synced to Wix: {result}")
        return result
        
    except Exception as e:
        print(f"✗ Error syncing to Wix: {e}")
        return {"error": str(e)}


@bp_wix_sync.route('/sync-wix', methods=['POST', 'GET'])
def sync_wix():
    """
    Sync Pipedrive deals to Wix collection using filter-based approach.
    
    Query params:
    - filter_id: Pipedrive filter ID (required) - returns ONLY deals matching that filter
    
    Usage:
    - GET /sync-wix?filter_id=<FILTER_ID>   # Sync deals from specific Pipedrive filter
    """
    filter_id = request.args.get('filter_id')
    if not filter_id:
        return jsonify({"error": "filter_id query parameter is required"}), 400
    
    print(f"✓ Using Pipedrive filter: {filter_id}")
    
    # Validate credentials
    if not all([WIX_API_KEY, WIX_SITE_ID, PIPEDRIVE_API_TOKEN]):
        return jsonify({"error": "Missing credentials"}), 500
    
    # Get field mapping
    field_map = _get_pipedrive_field_map()
    if not field_map:
        return jsonify({"error": "Could not fetch Pipedrive field map"}), 500
    
    print(f"✓ Built Pipedrive field map")
    
    # Fetch Pipedrive deals using filter (includes ALL custom fields)
    pipedrive_deals = _fetch_pipedrive_deals_filtered(filter_id)
    
    if not pipedrive_deals:
        return jsonify({"error": "No Pipedrive deals found for this filter"}), 400
    
    print(f"✓ Fetched {len(pipedrive_deals)} deals")
    
    # Sync to Wix with collection ID and field map
    wix_response = _sync_to_wix(WIX_COLLECTION_ID, pipedrive_deals, field_map)
    
    return jsonify({
        "status": "success",
        "deals_synced": len(pipedrive_deals),
        "filter_id": filter_id,
        "wix_response": wix_response
    }), 200
