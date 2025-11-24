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
    """Build field map with field metadata including option mappings for dropdowns"""
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
        field_options = {}  # Store option mappings: field_key → {option_id → label}
        
        for field in fields:
            name = field.get("name", "")
            key = field.get("key", "")
            field_map[name] = key
            
            # Build option mappings for dropdown/select fields
            options = field.get("options", [])
            if options:
                option_map = {}
                for opt in options:
                    opt_id = opt.get("id")
                    opt_label = opt.get("label")
                    if opt_id is not None and opt_label:
                        option_map[opt_id] = opt_label
                if option_map:
                    field_options[key] = option_map
        
        # Fetch and cache stage names
        stage_names = {}
        try:
            stages_response = requests.get(
                f"{PIPEDRIVE_BASE}/stages",
                params={"api_token": PIPEDRIVE_API_TOKEN, "limit": 500}
            )
            stages_response.raise_for_status()
            stages = stages_response.json().get("data", [])
            for stage in stages:
                stage_id = stage.get("id")
                stage_name = stage.get("name")
                if stage_id and stage_name:
                    stage_names[stage_id] = stage_name
        except Exception as e:
            print(f"Warning: Could not fetch stage names: {e}")
        
        # Return both the field map and options for use in conversion
        return {"field_map": field_map, "field_options": field_options, "stage_names": stage_names}
    except Exception as e:
        print(f"Error fetching Pipedrive field map: {e}")
        return None


def _fetch_pipedrive_deals_filtered(filter_id, limit=500):
    """Fetch deals using filter endpoint - fetches individually to include custom fields"""
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
        
        # First, get the list of deal IDs from the filter
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        filter_deals = response.json().get("data") or []
        deal_ids = [d.get("id") for d in filter_deals if d.get("id")]
        print(f"✓ Filter {filter_id} contains {len(deal_ids)} deals")
        
        # Now fetch each deal individually to ensure ALL custom fields are included
        # (filter_id endpoint doesn't return custom fields, but individual deal endpoint does)
        deals_with_custom_fields = []
        for deal_id in deal_ids:
            try:
                deal_response = requests.get(
                    f"{PIPEDRIVE_BASE}/deals/{deal_id}",
                    params={"api_token": PIPEDRIVE_API_TOKEN},
                    headers=headers
                )
                deal_response.raise_for_status()
                deal = deal_response.json().get("data")
                if deal:
                    deals_with_custom_fields.append(deal)
            except Exception as e:
                print(f"  Warning: Could not fetch deal {deal_id}: {e}")
                continue
        
        print(f"✓ Fetched {len(deals_with_custom_fields)} deals with ALL custom fields")
        return deals_with_custom_fields
    except Exception as e:
        print(f"Error fetching Pipedrive deals with filter: {e}")
        return []


def _build_wix_payload(deal, field_map, field_options=None, stage_names=None):
    """
    Convert a single Pipedrive deal into a Wix collection item dict.
    Pulls values using field_map to translate from display names to internal keys.
    Converts numeric option IDs to display labels using field_options.
    Outputs Wix field keys exactly as Wix expects.
    Skips placeholder images and broken URLs.
    """
    if field_options is None:
        field_options = {}
    if stage_names is None:
        stage_names = {}

    def get_field(display_name):
        """Get field value from deal using display name"""
        if not field_map:
            return None
        internal_key = field_map.get(display_name)
        if internal_key:
            value = deal.get(internal_key)
            # Convert numeric option IDs to labels if this field has options
            if value is not None and internal_key in field_options:
                # Handle both single values and lists
                if isinstance(value, list):
                    converted = []
                    for v in value:
                        # Try both the value as-is and as an integer
                        if v in field_options[internal_key]:
                            converted.append(field_options[internal_key][v])
                        elif isinstance(v, str) and v.isdigit() and int(v) in field_options[internal_key]:
                            converted.append(field_options[internal_key][int(v)])
                        else:
                            converted.append(v)
                    return ", ".join(str(x) for x in converted) if converted else None
                else:
                    # Handle comma-separated values (multi-value fields)
                    if isinstance(value, str) and "," in value:
                        converted = []
                        for v in value.split(","):
                            v = v.strip()
                            if v in field_options[internal_key]:
                                converted.append(field_options[internal_key][v])
                            elif v.isdigit() and int(v) in field_options[internal_key]:
                                converted.append(field_options[internal_key][int(v)])
                            else:
                                converted.append(v)
                        return ", ".join(str(x) for x in converted) if converted else None
                    # Single value
                    elif value in field_options[internal_key]:
                        return field_options[internal_key][value]
                    elif isinstance(value, str) and value.isdigit() and int(value) in field_options[internal_key]:
                        return field_options[internal_key][int(value)]
            return value
        return None

    # PIPEDRIVE → WIX FIELD MAPPING
    pipedrive = {
        "title": deal.get("title"),  # Standard field

        # Neighborhood fields
        "dealNeighborhood": get_field("Neighborhood (primary)"),
        "dealNeighborhoodAddressDetails": get_field("Neighborhood (address details)"),
        "neighborhoodSecondary": get_field("Neighborhood (secondary)"),

        # Core data
        "dealState": get_field("State"),
        "dealZipCode": get_field("Zip Code"),
        "dealMap": get_field("Map"),
        "dealSlugAddress": get_field("Slug Address"),
        "dealStage": stage_names.get(deal.get("stage_id"), deal.get("stage_id")),  # Convert stage ID to name
        "dealWebDescriptionCopy": get_field("Web Description Copy"),
        "dealOwnerWellspringWeblink": get_field("Partner Wellspring Weblink"),
        "dealFtPt": get_field("FT | PT Availability/ Requirement"),
        "dealProfessionUse": get_field("Profession | Use"),
        "dealProfessionUse2": get_field("Profession | Use2"),

        # Linking logic
        "unifiedNeighborhoodLink": get_field("Unified Neighborhood Link"),
        "neighborhoodLinkLocal": get_field("Neighborhood Link Local"),
    }

    # IMAGES (1–10) - skip placeholders and empty URLs
    for i in range(1, 11):
        pic_url = get_field(f"Picture {i}")
        # Skip if empty or placeholder
        if pic_url and "placeholder" not in pic_url.lower():
            pipedrive[f"dealPicture{i}"] = pic_url
        else:
            pipedrive[f"dealPicture{i}"] = None
        
        pipedrive[f"dealAltTextPic{i}"]    = get_field(f"Alt Text Pic {i}")
        pipedrive[f"dealTooltipPic{i}"]    = get_field(f"Tooltip Pic {i}")

    # WIX ITEM DICT (THIS IS WHAT GETS SENT TO THE API)
    # Use Pipedrive deal ID as Wix _id for fresh replace each time
    wix_item = {
        "_id": str(deal.get("id")),  # Use Pipedrive deal ID as the Wix record ID
        "dealId": str(deal.get("id")),  # Pipedrive deal ID as string for Text field
        "dealOrder": deal.get("stage_order_nr"),  # Order within pipeline stage
        "title": pipedrive["title"],

        "dealNeighborhood": pipedrive["dealNeighborhood"],
        "dealNeighborhoodAddressDetails": pipedrive["dealNeighborhoodAddressDetails"],
        "neighborhoodSecondary": pipedrive["neighborhoodSecondary"],

        "dealState": pipedrive["dealState"],
        "dealMap": pipedrive["dealMap"],
        "dealSlugAddress": pipedrive["dealSlugAddress"],
        "dealStage": pipedrive["dealStage"],
        "dealWebDescriptionCopy": pipedrive["dealWebDescriptionCopy"],
        "dealOwnerWellspringWeblink": pipedrive["dealOwnerWellspringWeblink"],
        "dealFtPt": pipedrive["dealFtPt"],
        "dealProfessionUse": pipedrive["dealProfessionUse"],
        "dealProfessionUse2": pipedrive["dealProfessionUse2"],

        "unifiedNeighborhoodLink": pipedrive["unifiedNeighborhoodLink"],
        "neighborhoodLink": pipedrive["neighborhoodLinkLocal"],
    }
    
    # Only include dealZipCode if it has a value (avoid type warning with None)
    if pipedrive["dealZipCode"]:
        wix_item["dealZipCode"] = str(pipedrive["dealZipCode"])
    
    # Inject pictures (1–10) - only if valid
    for i in range(1, 11):
        if pipedrive[f"dealPicture{i}"]:
            wix_item[f"dealPicture{i}"] = pipedrive[f"dealPicture{i}"]
        if pipedrive[f"dealAltTextPic{i}"]:
            wix_item[f"dealAltTextPic{i}"] = pipedrive[f"dealAltTextPic{i}"]
        if pipedrive[f"dealTooltipPic{i}"]:
            wix_item[f"dealTooltipPic{i}"] = pipedrive[f"dealTooltipPic{i}"]

    return wix_item


def _delete_from_wix(collection_id, deal_ids):
    """Delete existing items from Wix before fresh insert"""
    if not collection_id or not WIX_API_KEY or not WIX_SITE_ID or not deal_ids:
        return []
    
    try:
        headers = {
            "Authorization": f"Bearer {WIX_API_KEY}",
            "wix-site-id": WIX_SITE_ID,
            "Content-Type": "application/json"
        }
        
        delete_items = [{"_id": str(deal_id)} for deal_id in deal_ids]
        payload = {
            "dataCollectionId": collection_id,
            "dataItems": delete_items
        }
        
        bulk_delete_endpoint = f"{WIX_API_BASE}/bulk/items/remove"
        print(f"Deleting {len(delete_items)} items from Wix...")
        
        response = requests.post(
            bulk_delete_endpoint,
            headers=headers,
            json=payload
        )
        
        print(f"Delete response: {response.status_code}")
        
        # Ignore 404 errors (items don't exist yet)
        if response.status_code in [200, 404]:
            return deal_ids
        else:
            response.raise_for_status()
            return deal_ids
    except Exception as e:
        print(f"Note: Delete operation completed (may have no items to delete): {e}")
        return deal_ids


def _sync_to_wix(collection_id, pipedrive_deals, field_map, field_options=None, stage_names=None):
    """
    Fresh sync to Wix: delete existing records then insert new ones
    This ensures true "replace all" behavior each time
    """
    if field_options is None:
        field_options = {}
    if stage_names is None:
        stage_names = {}
    
    if not collection_id or not WIX_API_KEY or not WIX_SITE_ID or not pipedrive_deals:
        return {"error": "Missing collection_id, credentials, or deals"}
    
    try:
        # Extract deal IDs for deletion
        deal_ids = [deal.get("id") for deal in pipedrive_deals]
        
        # Step 1: Delete existing items
        print("\n=== STEP 1: DELETE EXISTING ITEMS ===")
        _delete_from_wix(collection_id, deal_ids)
        
        # Step 2: Build and insert fresh items
        print("\n=== STEP 2: INSERT FRESH ITEMS ===")
        data_items = []
        
        for deal in pipedrive_deals:
            # Build Wix item data with field option mappings and stage names
            item_data = _build_wix_payload(deal, field_map, field_options, stage_names)
            # Wrap in Wix data structure
            data_items.append({
                "_id": item_data.pop("_id"),  # Extract _id (Pipedrive deal ID)
                "data": item_data  # Remaining fields go in data
            })
        
        headers = {
            "Authorization": f"Bearer {WIX_API_KEY}",
            "wix-site-id": WIX_SITE_ID,
            "Content-Type": "application/json"
        }
        
        # Wix REST API payload structure
        payload = {
            "dataCollectionId": collection_id,
            "dataItems": data_items
        }
        
        print(f"Syncing {len(data_items)} items to Wix collection '{collection_id}'...")
        
        bulk_endpoint = f"{WIX_API_BASE}/bulk/items/save"
        
        response = requests.post(
            bulk_endpoint,
            headers=headers,
            json=payload
        )
        
        print(f"Insert response: {response.status_code}")
        
        response.raise_for_status()
        
        result = response.json()
        print(f"✓ Fresh sync completed: {result.get('bulkActionMetadata', {})}")
        return result
        
    except Exception as e:
        print(f"✗ Error syncing to Wix: {e}")
        return {"error": str(e)}


def _fetch_pipedrive_deals_by_neighborhood(neighborhood_name, neighborhood_id=None):
    """Fetch deals from master neighborhood filter (filter_id 210) - PRIMARY neighborhoods only"""
    if not PIPEDRIVE_API_TOKEN:
        return []
    
    try:
        # Use filter 210 to get PRIMARY neighborhoods only (this is your master filter)
        url = f"{PIPEDRIVE_BASE}/deals"
        params = {
            "api_token": PIPEDRIVE_API_TOKEN,
            "filter_id": 210,  # Master neighborhood filter for primary neighborhoods
            "limit": 500
        }
        
        all_deal_ids = []
        while True:
            response = requests.get(url, params=params).json()
            deals = response.get("data") or []
            if not deals:
                break
            all_deal_ids.extend([d.get("id") for d in deals if d.get("id")])
            
            # Pagination
            pagination = response.get("additional_data", {}).get("pagination", {})
            if not pagination.get("next_start"):
                break
            params["start"] = pagination["next_start"]
        
        print(f"✓ Filter 210 contains {len(all_deal_ids)} deals")
        
        # Fetch each deal individually to ensure ALL custom fields are included
        headers = {"Accept": "application/json"}
        all_deals_with_fields = []
        for deal_id in all_deal_ids:
            try:
                deal_response = requests.get(
                    f"{PIPEDRIVE_BASE}/deals/{deal_id}",
                    params={"api_token": PIPEDRIVE_API_TOKEN},
                    headers=headers
                )
                deal_response.raise_for_status()
                deal = deal_response.json().get("data")
                if deal:
                    all_deals_with_fields.append(deal)
            except Exception as e:
                print(f"  Warning: Could not fetch deal {deal_id}: {e}")
                continue
        
        print(f"✓ Fetched {len(all_deals_with_fields)} deals with ALL custom fields")
        
        # If no specific neighborhood_id provided, return all (for bulk sync)
        if not neighborhood_id and not neighborhood_name:
            return all_deals_with_fields
        
        # Get field info to filter by specific neighborhood
        fields_response = requests.get(
            f"{PIPEDRIVE_BASE}/dealFields",
            params={"api_token": PIPEDRIVE_API_TOKEN}
        ).json()
        
        neighborhood_key = None
        neighborhood_options = {}
        for field in fields_response.get("data", []):
            if field.get("name") == "Neighborhood (primary)":
                neighborhood_key = field.get("key")
                # Build ID to label mapping
                for opt in field.get("options", []):
                    neighborhood_options[opt.get("id")] = opt.get("label")
                break
        
        if not neighborhood_key:
            print(f"Warning: Could not find Neighborhood field key")
            return all_deals_with_fields
        
        # Determine which ID(s) to match
        target_id = neighborhood_id
        if not target_id and neighborhood_name:
            # Try to find the ID from the neighborhood name
            for opt_id, opt_label in neighborhood_options.items():
                if opt_label == neighborhood_name or neighborhood_name in opt_label:
                    target_id = opt_id
                    break
        
        if not target_id:
            # No specific neighborhood filter, return all from master filter
            return all_deals_with_fields
        
        # Filter deals by the specific neighborhood ID
        filtered_deals = []
        for deal in all_deals_with_fields:
            hood_data = deal.get(neighborhood_key)
            if hood_data:
                # Check if this is the exact neighborhood (PRIMARY)
                if hood_data == target_id or hood_data == str(target_id):
                    filtered_deals.append(deal)
        
        print(f"✓ Filtered to {len(filtered_deals)} deals from neighborhood ID {target_id}")
        return filtered_deals
        
    except Exception as e:
        print(f"Error fetching Pipedrive deals by neighborhood: {e}")
        return []


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
    
    # Get field mapping, options, and stage names
    field_data = _get_pipedrive_field_map()
    if not field_data:
        return jsonify({"error": "Could not fetch Pipedrive field map"}), 500
    
    field_map = field_data.get("field_map", {})
    field_options = field_data.get("field_options", {})
    stage_names = field_data.get("stage_names", {})
    
    # Fetch Pipedrive deals using filter (includes ALL custom fields)
    pipedrive_deals = _fetch_pipedrive_deals_filtered(filter_id)
    
    if not pipedrive_deals:
        return jsonify({"error": "No Pipedrive deals found for this filter"}), 400
    
    print(f"✓ Fetched {len(pipedrive_deals)} deals")
    
    # Sync to Wix with collection ID, field map, field options, and stage names
    wix_response = _sync_to_wix(WIX_COLLECTION_ID, pipedrive_deals, field_map, field_options, stage_names)
    
    return jsonify({
        "status": "success",
        "deals_synced": len(pipedrive_deals),
        "filter_id": filter_id,
        "wix_response": wix_response
    }), 200


@bp_wix_sync.route('/sync-neighborhood', methods=['POST', 'GET'])
def sync_neighborhood():
    """
    Sync Pipedrive deals to Wix collection by neighborhood name or ID.
    
    Query params:
    - neighborhood: Neighborhood name (e.g., "Upper East Side")
    - neighborhood_id: Optional neighborhood ID (e.g., 63) - overrides name lookup
    
    Usage:
    - GET /sync-neighborhood?neighborhood=Upper%20East%20Side
    - GET /sync-neighborhood?neighborhood_id=63
    """
    neighborhood = request.args.get('neighborhood', '')
    neighborhood_id = request.args.get('neighborhood_id')
    
    if not neighborhood and not neighborhood_id:
        return jsonify({"error": "Either neighborhood or neighborhood_id parameter is required"}), 400
    
    print(f"✓ Syncing neighborhood: {neighborhood or f'ID {neighborhood_id}'}")
    
    # Validate credentials
    if not all([WIX_API_KEY, WIX_SITE_ID, PIPEDRIVE_API_TOKEN]):
        return jsonify({"error": "Missing credentials"}), 500
    
    # Get field mapping, options, and stage names
    field_data = _get_pipedrive_field_map()
    if not field_data:
        return jsonify({"error": "Could not fetch Pipedrive field map"}), 500
    
    field_map = field_data.get("field_map", {})
    field_options = field_data.get("field_options", {})
    stage_names = field_data.get("stage_names", {})
    
    # Fetch Pipedrive deals by neighborhood
    pipedrive_deals = _fetch_pipedrive_deals_by_neighborhood(neighborhood, neighborhood_id)
    
    if not pipedrive_deals:
        return jsonify({"error": f"No deals found for neighborhood: {neighborhood or neighborhood_id}"}), 400
    
    print(f"✓ Fetched {len(pipedrive_deals)} deals")
    
    # Sync to Wix with collection ID, field map, field options, and stage names
    wix_response = _sync_to_wix(WIX_COLLECTION_ID, pipedrive_deals, field_map, field_options, stage_names)
    
    return jsonify({
        "status": "success",
        "deals_synced": len(pipedrive_deals),
        "neighborhood": neighborhood or f"ID {neighborhood_id}",
        "wix_response": wix_response
    }), 200
