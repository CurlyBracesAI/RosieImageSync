from flask import Blueprint, jsonify, request
import boto3
import json
import os
import requests
from openai import OpenAI

def _get_pipedrive_api_token():
    """Get Pipedrive API token from environment"""
    return os.environ.get("PIPEDRIVE_API_TOKEN")

def _get_pipedrive_field_keys():
    """Get Pipedrive custom field keys for Alt Text and Tooltip fields"""
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
        print(f"Error fetching Pipedrive field keys: {e}")
        return None

def _update_pipedrive_deal(deal_id, images):
    """Update Pipedrive deal with alt text and tooltip data"""
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
    for i, image in enumerate(images, start=1):
        if i > 10:  # Only handle first 10 images
            break
        
        if i in field_map:
            if "alt" in field_map[i] and image.get("alt_text"):
                update_data[field_map[i]["alt"]] = image["alt_text"]
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
        print(f"Successfully updated Pipedrive deal {deal_id}")
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

def _generate_descriptions(neighborhood, labels, url):
    client = _get_openai_client()
    if not client:
        return {"alt_text": "", "tooltip_text": ""}
    
    try:
        labels_str = ", ".join(labels) if labels else "no labels detected"
        prompt = f"""Generate simple, factual descriptions for a commercial office property image.

Detected elements: {labels_str}
Location: {neighborhood}
Property type: Professional office space for psychotherapists, wellness and medical professionals

CRITICAL RULES:
- Keep descriptions SHORT and FACTUAL - describe only what's visible
- Use the detected elements directly, don't embellish or add promotional language
- NO flowery language, NO selling, NO assumptions beyond what's detected
- VARY the sentence structure - don't use the same pattern every time
- Be professional and descriptive, not promotional
- Reference the location as "{neighborhood}" - DO NOT mention image URLs, file paths, or technical references

Return JSON with:
- alt_text: VERY SHORT - exactly 8-14 words. Describe the scene functionally for screen readers.
- tooltip_text: Slightly longer - exactly 20-30 words. More descriptive for the website visitor, but still lean and factual.

Example variations (all good - notice different structures):
{{"alt_text": "Modern office entrance with glass doors and reception area", "tooltip_text": "Commercial office building in {neighborhood} with accessible entrance and reception space for therapy and medical practices."}}

{{"alt_text": "Office interior showing desk, chairs, and natural window lighting", "tooltip_text": "Furnished office space in {neighborhood} features natural light, seating area, and workspace setup for professional practices."}}

{{"alt_text": "Building exterior with brick facade and street-level entrance", "tooltip_text": "Multi-story office building located in {neighborhood}, offering commercial space for healthcare and wellness professionals."}}

Example BAD (promotional or repetitive):
{{"alt_text": "Professional office space suitable for wellness professionals", "tooltip_text": "Professional office space in {neighborhood} suitable for therapists and medical professionals seeking office space."}}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "alt_text": result.get("alt_text", ""),
            "tooltip_text": result.get("tooltip_text", "")
        }
    except Exception:
        return {"alt_text": "", "tooltip_text": ""}

bp_rosie_images = Blueprint("rosie_images", __name__)

@bp_rosie_images.route("/rosie-images", methods=["POST"])
def rosie_images():
    data = request.get_json(silent=True)
    
    if data is None:
        data = request.form.to_dict()
        if 'image_urls' in data:
            try:
                data['image_urls'] = json.loads(data['image_urls'])
            except:
                data['image_urls'] = [url.strip() for url in data['image_urls'].split(',')]
    
    if not data:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    deal_id = data.get("deal_id")
    neighborhood = data.get("neighborhood")
    image_urls = data.get("image_urls")
    
    if not deal_id or not neighborhood or image_urls is None:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    # Clean neighborhood: extract just the neighborhood name from path like "Neighborhood Listing Images/Upper West Side/2560/1.jpg"
    if "/" in neighborhood:
        parts = neighborhood.split("/")
        if len(parts) >= 2 and parts[0] == "Neighborhood Listing Images":
            neighborhood = parts[1]
    
    processed = []
    for url in image_urls:
        image_bytes = _fetch_image_bytes(url)
        labels = _detect_labels(image_bytes)
        descriptions = _generate_descriptions(neighborhood, labels, url)
        processed.append({
            "url": url,
            "status": "processed",
            "bytes_fetched": image_bytes is not None,
            "labels": labels,
            "alt_text": descriptions.get("alt_text", ""),
            "tooltip_text": descriptions.get("tooltip_text", "")
        })
    
    # Update Pipedrive with alt text and tooltip data
    pipedrive_updated = _update_pipedrive_deal(deal_id, processed)
    
    return jsonify({
        "status": "ok",
        "deal_id": deal_id,
        "neighborhood": neighborhood,
        "image_count": len(image_urls),
        "images": processed,
        "pipedrive_updated": pipedrive_updated
    })
