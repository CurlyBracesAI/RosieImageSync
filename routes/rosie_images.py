from flask import Blueprint, jsonify, request
import boto3
import json
import os
import requests
from openai import OpenAI

WIX_API_KEY = os.getenv("WIX_ACCESS_KEY_ID")
WIX_SITE_ID = os.getenv("WIX_SITE_ID")
WIX_COLLECTION_ID = "Import455"
WIX_API_BASE = "https://www.wixapis.com/wix-data/v2"
PIPEDRIVE_BASE = "https://api.pipedrive.com/v1"

def _get_pipedrive_api_token():
    """Get Pipedrive API token from environment"""
    return os.environ.get("PIPEDRIVE_API_TOKEN")

def _get_deal_address(deal_id):
    """Fetch the address of a deal from Pipedrive"""
    token = _get_pipedrive_api_token()
    if not token:
        return None
    
    try:
        response = requests.get(
            f"https://api.pipedrive.com/v1/deals/{deal_id}",
            params={"api_token": token}
        )
        response.raise_for_status()
        deal_data = response.json().get("data", {})
        
        # Try custom field "Neighborhood (address details)" first
        address = deal_data.get("056689a92ce6b5049bf4b1293931c9fad5325c5f")
        if address:
            return address.strip()
        
        # Fallback to standard address field
        address = deal_data.get("address")
        if address:
            return address.strip()
        
        return None
    except Exception as e:
        print(f"Error fetching deal address for {deal_id}: {e}")
        return None

def _get_pipedrive_field_keys():
    """Get Pipedrive custom field keys for Picture URLs, Alt Text, and Tooltip fields"""
    token = _get_pipedrive_api_token()
    if not token:
        return None
    
    try:
        response = requests.get(
            "https://api.pipedrive.com/v1/dealFields",
            params={"api_token": token}
        )
        response.raise_for_status()
        fields = response.json().get("data", [])
        
        # Build mapping: {1: {picture: "key123", alt: "key456", tooltip: "key789"}, 2: {...}, ...}
        field_map = {}
        for field in fields:
            name = field.get("name", "")
            key = field.get("key", "")
            
            # Match "Picture 1" through "Picture 10"
            if name.startswith("Picture "):
                pic_num = name.split("Picture")[-1].strip()
                try:
                    num = int(pic_num)
                    if num not in field_map:
                        field_map[num] = {}
                    field_map[num]["picture"] = key
                except ValueError:
                    pass
            
            # Match "Deal - Alt Text Pic 1" through "Deal - Alt Text Pic 10"
            elif "Alt Text Pic" in name:
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
        print(f"Error fetching Pipedrive field keys: {e}")
        return None

def _check_pipedrive_slot_populated(deal_id, picture_number):
    """Check if a specific picture slot already has alt_text and tooltip_text populated
    
    Args:
        deal_id: Pipedrive deal ID
        picture_number: Picture slot to check (1-10)
    
    Returns:
        dict with {alt_text: str, tooltip_text: str} if populated, None otherwise
    """
    if picture_number is None or picture_number < 1 or picture_number > 10:
        print(f"Cache check failed: invalid picture_number {picture_number}")
        return None
    
    token = _get_pipedrive_api_token()
    if not token:
        print(f"Cache check failed: no Pipedrive token")
        return None
    
    field_map = _get_pipedrive_field_keys()
    if not field_map or picture_number not in field_map:
        print(f"Cache check failed: field_map issue - field_map exists: {field_map is not None}, picture_number in map: {picture_number in field_map if field_map else False}")
        return None
    
    try:
        response = requests.get(
            f"https://api.pipedrive.com/v1/deals/{deal_id}",
            params={"api_token": token}
        )
        response.raise_for_status()
        deal_data = response.json().get("data", {})
        
        alt_key = field_map[picture_number].get("alt")
        tooltip_key = field_map[picture_number].get("tooltip")
        
        alt_text = (deal_data.get(alt_key) or "").strip() if alt_key else ""
        tooltip_text = (deal_data.get(tooltip_key) or "").strip() if tooltip_key else ""
        
        print(f"Cache check for deal {deal_id} pic {picture_number}: alt_text='{alt_text[:30] if alt_text else ''}...', tooltip_text='{tooltip_text[:30] if tooltip_text else ''}...'")
        
        if alt_text and tooltip_text:
            print(f"✓ Both fields populated, returning cached data")
            return {"alt_text": alt_text, "tooltip_text": tooltip_text}
        
        print(f"✗ Cache miss: alt_text empty={not alt_text}, tooltip_text empty={not tooltip_text}")
        return None
    except Exception as e:
        print(f"Error checking Pipedrive deal {deal_id}: {e}")
        return None

def _update_pipedrive_deal(deal_id, images, picture_number=None):
    """Update Pipedrive deal with picture URLs, alt text, and tooltip data
    
    Args:
        deal_id: Pipedrive deal ID
        images: List of image objects with url, alt_text, and tooltip_text
        picture_number: Optional specific picture slot (1-10) to update. If None, updates slots 1-N based on array position
    """
    token = _get_pipedrive_api_token()
    if not token:
        print("No Pipedrive API token found")
        return False
    
    field_map = _get_pipedrive_field_keys()
    if not field_map:
        print("Could not fetch Pipedrive field keys")
        return False
    
    # Build update payload
    update_data = {}
    
    if picture_number is not None:
        # Update specific picture slot
        if 1 <= picture_number <= 10 and len(images) > 0:
            image = images[0]  # Use first image in array
            if picture_number in field_map:
                # Update picture URL
                if "picture" in field_map[picture_number] and image.get("url"):
                    update_data[field_map[picture_number]["picture"]] = image["url"]
                # Update alt text
                if "alt" in field_map[picture_number] and image.get("alt_text"):
                    update_data[field_map[picture_number]["alt"]] = image["alt_text"]
                # Update tooltip text
                if "tooltip" in field_map[picture_number] and image.get("tooltip_text"):
                    update_data[field_map[picture_number]["tooltip"]] = image["tooltip_text"]
    else:
        # Update slots 1-N based on array position
        for i, image in enumerate(images, start=1):
            if i > 10:  # Only handle first 10 images
                break
            
            if i in field_map:
                # Update picture URL
                if "picture" in field_map[i] and image.get("url"):
                    update_data[field_map[i]["picture"]] = image["url"]
                # Update alt text
                if "alt" in field_map[i] and image.get("alt_text"):
                    update_data[field_map[i]["alt"]] = image["alt_text"]
                # Update tooltip text
                if "tooltip" in field_map[i] and image.get("tooltip_text"):
                    update_data[field_map[i]["tooltip"]] = image["tooltip_text"]
    
    if not update_data:
        print("No data to update in Pipedrive")
        return False
    
    # Update the deal
    try:
        response = requests.put(
            f"https://api.pipedrive.com/v1/deals/{deal_id}",
            params={"api_token": token},
            json=update_data
        )
        response.raise_for_status()
        print(f"Successfully updated Pipedrive deal {deal_id}, picture slot {picture_number if picture_number else '1-' + str(len(images))}")
        return True
    except Exception as e:
        print(f"Error updating Pipedrive deal: {e}")
        return False

def _get_openai_client():
    """Lazy-load OpenAI client to pick up secrets at runtime"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return OpenAI(api_key=api_key)
    return None

def _get_rekognition_client():
    """Lazy-load AWS Rekognition client to pick up secrets at runtime"""
    region = os.environ.get("AWS_REGION")
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    
    if all([region, access_key, secret_key]):
        return boto3.client(
            "rekognition",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    return None

def _fetch_image_bytes(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception:
        return None

def _detect_labels(image_bytes):
    if image_bytes is None:
        return []
    
    rekognition = _get_rekognition_client()
    if not rekognition:
        return []
    
    try:
        response = rekognition.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=10,
            MinConfidence=75
        )
        labels = [label["Name"] for label in response.get("Labels", [])]
        return labels
    except Exception:
        return []

def _generate_descriptions(neighborhood, labels, url, address=None):
    client = _get_openai_client()
    if not client:
        return {"alt_text": "", "tooltip_text": ""}
    
    try:
        labels_str = ", ".join(labels) if labels else "no labels detected"
        
        # Use address for descriptions, fallback to neighborhood if address is not available
        location_ref = address if address else neighborhood
        
        prompt = f"""Generate simple, factual descriptions for a commercial office property image.

Detected elements: {labels_str}
Location: {location_ref}
Property type: Professional office space for psychotherapists, wellness and medical professionals

CRITICAL RULES:
- Keep descriptions SHORT and FACTUAL - describe only what's visible
- Use the detected elements directly, don't embellish or add promotional language
- NO flowery language, NO selling, NO assumptions beyond what's detected
- VARY the sentence structure - don't use the same pattern every time
- Be professional and descriptive, not promotional
- DO NOT mention image URLs, file paths, or technical references

Return JSON with:
- alt_text: VERY SHORT - exactly 8-14 words. Describe the scene functionally for screen readers.
- tooltip_text: Slightly longer - exactly 20-30 words. More descriptive scene details for the website visitor, but still lean and factual.

Example variations (all good - notice different structures):
{{"alt_text": "Modern office entrance with glass doors and reception area", "tooltip_text": "Commercial office at {location_ref} features accessible entrance and reception area suitable for therapy and medical practices."}}

{{"alt_text": "Office interior showing desk, chairs, and natural window lighting", "tooltip_text": "Furnished office at {location_ref} offers natural light, comfortable seating area, and workspace setup for professional practices."}}

{{"alt_text": "Building exterior with brick facade and street-level entrance", "tooltip_text": "Office building at {location_ref} provides professional commercial space for healthcare and wellness professionals."}}

Example BAD (promotional or repetitive):
{{"alt_text": "Professional office space suitable for wellness professionals", "tooltip_text": "Professional office space suitable for therapists and medical professionals seeking office space."}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content or "{}"
        result = json.loads(content)
        
        return {
            "alt_text": result.get("alt_text", ""),
            "tooltip_text": result.get("tooltip_text", "")
        }
    except Exception:
        return {"alt_text": "", "tooltip_text": ""}

def _sync_deal_to_wix(deal_id):
    """Sync a single deal from Pipedrive to Wix after image processing"""
    from routes.wix_sync import _get_pipedrive_field_map, _build_wix_payload
    
    wix_api_key = os.getenv("WIX_ACCESS_KEY_ID")
    wix_site_id = os.getenv("WIX_SITE_ID")
    pipedrive_token = os.getenv("PIPEDRIVE_API_TOKEN")
    
    if not all([wix_api_key, wix_site_id, pipedrive_token]):
        print(f"⚠️ Wix sync skipped: missing credentials")
        return {"synced": False, "error": "Missing Wix/Pipedrive credentials"}
    
    try:
        field_data = _get_pipedrive_field_map()
        if not field_data:
            return {"synced": False, "error": "Could not fetch field map"}
        
        field_map = field_data.get("field_map", {})
        field_options = field_data.get("field_options", {})
        stage_names = field_data.get("stage_names", {})
        
        response = requests.get(
            f"{PIPEDRIVE_BASE}/deals/{deal_id}",
            params={"api_token": pipedrive_token}
        )
        response.raise_for_status()
        deal = response.json().get("data")
        
        if not deal:
            return {"synced": False, "error": f"Deal {deal_id} not found"}
        
        item_data = _build_wix_payload(deal, field_map, field_options, stage_names)
        
        data_items = [{
            "_id": item_data.pop("_id"),
            "data": item_data
        }]
        
        headers = {
            "Authorization": f"Bearer {wix_api_key}",
            "wix-site-id": wix_site_id,
            "Content-Type": "application/json"
        }
        
        payload = {
            "dataCollectionId": WIX_COLLECTION_ID,
            "dataItems": data_items
        }
        
        print(f"Syncing deal {deal_id} to Wix...")
        wix_response = requests.post(
            f"{WIX_API_BASE}/bulk/items/save",
            headers=headers,
            json=payload
        )
        wix_response.raise_for_status()
        result = wix_response.json()
        
        metadata = result.get('bulkActionMetadata', {})
        print(f"✓ Wix sync completed for deal {deal_id}: {metadata}")
        
        return {
            "synced": True,
            "totalSuccesses": metadata.get("totalSuccesses", 0),
            "totalFailures": metadata.get("totalFailures", 0)
        }
        
    except Exception as e:
        print(f"✗ Wix sync failed for deal {deal_id}: {e}")
        return {"synced": False, "error": str(e)}

bp_rosie_images = Blueprint("rosie_images", __name__)

@bp_rosie_images.route("/rosie-images", methods=["POST"])
def rosie_images():
    data = request.get_json(silent=True)
    
    if data is None:
        data = request.form.to_dict()
        if 'image_urls' in data:
            image_urls_str = data['image_urls']
            try:
                parsed = json.loads(image_urls_str) if isinstance(image_urls_str, str) else image_urls_str
                data['image_urls'] = parsed  # type: ignore
            except:
                if isinstance(image_urls_str, str):
                    data['image_urls'] = [url.strip() for url in image_urls_str.split(',')]  # type: ignore
    
    if not data:
        print(f"ERROR: No data received")
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    deal_id = data.get("deal_id")
    neighborhood = data.get("neighborhood")
    image_urls = data.get("image_urls")
    picture_number = data.get("picture_number")
    force_refresh = data.get("force_refresh", False)
    
    # Convert force_refresh to boolean
    if isinstance(force_refresh, str):
        force_refresh = force_refresh.lower() in ('true', '1', 'yes')
    
    if not deal_id or not neighborhood or image_urls is None:
        print(f"ERROR: Missing fields - deal_id={deal_id}, neighborhood={neighborhood}, image_urls={image_urls}")
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    # Convert deal_id to integer
    try:
        deal_id = int(deal_id)
    except (ValueError, TypeError):
        print(f"ERROR: Invalid deal_id '{deal_id}' - must be numeric")
        return jsonify({"status": "error", "message": "deal_id must be a valid integer"}), 400
    
    # Validate picture_number if provided
    if picture_number is not None:
        try:
            picture_number = int(picture_number)
            if picture_number < 1 or picture_number > 10:
                return jsonify({"status": "error", "message": "picture_number must be between 1 and 10"}), 400
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "picture_number must be a valid integer"}), 400
    
    
    # Auto-detect picture_number from URL if not provided
    # URL format: .../2560/1.jpeg or .../2560/2.jpeg
    if picture_number is None and len(image_urls) == 1:
        filename = ""
        try:
            url_path = image_urls[0].split('/')[-1]
            filename = url_path.split('.')[0]
            print(f"Auto-detect: URL={image_urls[0][-50:]}, filename={filename}")
            picture_number = int(filename)
            if picture_number < 1 or picture_number > 10:
                print(f"Auto-detect: Number {picture_number} out of range, setting to None")
                picture_number = None
            else:
                print(f"✓ Auto-detected picture_number: {picture_number}")
        except (ValueError, IndexError) as e:
            print(f"Auto-detect failed: filename='{filename}', error={e}")
            picture_number = None
    
    # Fetch deal address from Pipedrive
    address = _get_deal_address(deal_id)
    if address:
        print(f"✓ Got address for deal {deal_id}: {address}")
    else:
        print(f"⚠️ No address found for deal {deal_id}, will use neighborhood in descriptions")
    
    # Check if this picture slot is already populated (skip expensive processing)
    # Skip cache check if force_refresh is true
    print(f"Checking cache for deal {deal_id}, picture {picture_number}, force_refresh={force_refresh}")
    existing_data = None if force_refresh else _check_pipedrive_slot_populated(deal_id, picture_number)
    if existing_data:
        print(f"✓ CACHE HIT: Skipping deal {deal_id}, picture slot {picture_number} - already populated")
        return jsonify({
            "status": "ok",
            "deal_id": deal_id,
            "neighborhood": neighborhood,
            "image_count": len(image_urls),
            "picture_number": picture_number,
            "images": [{
                "url": image_urls[0] if image_urls else "",
                "status": "cached",
                "bytes_fetched": True,
                "labels": [],
                "alt_text": existing_data["alt_text"],
                "tooltip_text": existing_data["tooltip_text"]
            }],
            "pipedrive_updated": False,
            "cached": True
        })
    
    # Process images normally
    processed = []
    for url in image_urls:
        image_bytes = _fetch_image_bytes(url)
        labels = _detect_labels(image_bytes)
        descriptions = _generate_descriptions(neighborhood, labels, url, address=address)
        processed.append({
            "url": url,
            "status": "processed",
            "bytes_fetched": image_bytes is not None,
            "labels": labels,
            "alt_text": descriptions.get("alt_text", ""),
            "tooltip_text": descriptions.get("tooltip_text", "")
        })
    
    # Update Pipedrive with alt text and tooltip data
    pipedrive_updated = _update_pipedrive_deal(deal_id, processed, picture_number)
    
    # Sync deal to Wix automatically after processing
    wix_result = _sync_deal_to_wix(deal_id)
    
    return jsonify({
        "status": "ok",
        "deal_id": deal_id,
        "neighborhood": neighborhood,
        "image_count": len(image_urls),
        "picture_number": picture_number,
        "images": processed,
        "pipedrive_updated": pipedrive_updated,
        "wix_synced": wix_result
    })
