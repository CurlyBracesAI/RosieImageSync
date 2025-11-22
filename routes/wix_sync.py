from flask import Blueprint, jsonify, request
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
        
        print(f"Collection '{WIX_COLLECTION_NAME}' not found")
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


def _fetch_pipedrive_deals(neighborhood_filter=None):
    """Fetch all open deals from Pipedrive, optionally filtered by neighborhood"""
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


def _build_wix_payload(pipedrive_deal, field_map):
    """Convert Pipedrive deal to Wix item data payload using exact Pipedrive field names"""
    if not field_map:
        return {}
    
    data = {}
    
    # Use exact Pipedrive display names - NO "Deal - " prefix
    field_mappings = {
        "ID (Wix)": "dealId",
        "Title": "title",
        "Order": "dealOrder",
        "Neighborhood (primary)": "dealNeighborhood",
        "Neighborhood (secondary)": "neighborhoodSecondary",
        "Neighborhood (address details)": "dealNeighborhoodAddressDetails",
        "State": "dealState",
        "Zip Code": "dealZipCode",
        "Web Description Copy": "dealWebDescriptionCopy",
        "Partner Wellspring Weblink": "dealOwnerWellspringWeblink",
        "FT | PT Availability/ Requirement": "dealFtPt",
        "Profession | Use": "dealProfessionUse",
        "Profession | Use2": "dealProfessionUse2",
        "Unified Neighborhood Link": "unifiedNeighborhoodLink",
        "Neighborhood Link Local": "neighborhoodLinkLocal",
        "Slug Address": "slugAddress",
        "Map": "map",
    }
    
    # Add picture + alt/tooltip fields (1-10)
    for i in range(1, 11):
        field_mappings[f"Picture {i}"] = f"dealPicture{i}"
        field_mappings[f"Alt Text Pic {i}"] = f"dealAltTextPic{i}"
        field_mappings[f"Tooltip Pic {i}"] = f"dealTooltipPic{i}"
    
    # Map Pipedrive fields to Wix payload
    for pd_field, wix_key in field_mappings.items():
        pd_key = field_map.get(pd_field)
        value = pipedrive_deal.get(pd_key) if pd_key else None
        if value is not None and value != "":
            data[wix_key] = value
    
    return data


def _sync_to_wix(collection_id, pipedrive_deals, field_map):
    """
    Sync Pipedrive deals to Wix by matching Pipedrive ID field.
    Wix items already have Pipedrive IDs in their "ID" field.
    """
    if not collection_id or not WIX_API_KEY or not WIX_SITE_ID or not pipedrive_deals:
        return {"error": "Missing collection_id, credentials, or deals"}
    
    try:
        wix_items = []
        
        for deal in pipedrive_deals:
            deal_id = deal.get("id")
            
            item_data = _build_wix_payload(deal, field_map)
            item_data["ID"] = str(deal_id)  # Ensure Pipedrive ID is in payload
            
            # For bulk save, wrap each item with {"data": ...}
            # Don't include _id for new items; Wix will generate it
            wix_items.append({
                "data": item_data
            })
        
        headers = {
            "Authorization": WIX_API_KEY,
            "wix-site-id": WIX_SITE_ID,
            "Content-Type": "application/json"
        }
        
        # Correct Wix bulk save structure - use collectionName, not collectionId
        payload = {
            "bulkOperation": {
                "collectionName": WIX_COLLECTION_NAME,
                "items": wix_items
            }
        }
        
        print(f"Syncing {len(wix_items)} items to Wix...")
        if len(wix_items) > 0:
            print(f"Sample item data fields: {list(wix_items[0].get('data', {}).keys())}")
        
        # Correct Wix API endpoint (v2 without collections path)
        bulk_endpoint = f"{WIX_API_BASE}/bulk/items/save"
        
        response = requests.post(
            bulk_endpoint,
            headers=headers,
            json=payload
        )
        
        # Print detailed error info before raising
        if response.status_code >= 400:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            if len(wix_items) > 0:
                print(f"First item data: {wix_items[0]}")
        
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
    Sync Pipedrive deals to Wix collection.
    
    Query params:
    - neighborhood: Filter by neighborhood (e.g., "Upper West Side")
    
    Usage:
    - GET /sync-wix                                    # Sync all neighborhoods
    - GET /sync-wix?neighborhood=Upper%20West%20Side   # Sync one neighborhood
    """
    neighborhood_filter = request.args.get('neighborhood')
    if neighborhood_filter:
        print(f"✓ Filtering by neighborhood: {neighborhood_filter}")
    
    # Validate credentials
    if not all([WIX_API_KEY, WIX_SITE_ID, PIPEDRIVE_API_TOKEN]):
        return jsonify({
            "error": "Missing credentials"
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
    pipedrive_deals = _fetch_pipedrive_deals()
    
    if not pipedrive_deals:
        return jsonify({"error": "No Pipedrive deals found"}), 400
    
    # Filter by neighborhood if specified
    if neighborhood_filter and field_map:
        neighborhood_key = field_map.get("Neighborhood (primary)")
        if neighborhood_key:
            filtered_deals = []
            for deal in pipedrive_deals:
                deal_neighborhood = deal.get(neighborhood_key, "")
                if neighborhood_filter.lower() in deal_neighborhood.lower():
                    filtered_deals.append(deal)
            print(f"✓ Filtered to {len(filtered_deals)} deals in {neighborhood_filter}")
            pipedrive_deals = filtered_deals
    
    if not pipedrive_deals:
        return jsonify({
            "message": "No deals found for specified neighborhood",
            "neighborhood": neighborhood_filter
        }), 200
    
    # Sync to Wix
    wix_response = _sync_to_wix(collection_id, pipedrive_deals, field_map)
    
    return jsonify({
        "status": "success",
        "deals_synced": len(pipedrive_deals),
        "neighborhood": neighborhood_filter,
        "wix_response": wix_response
    }), 200
