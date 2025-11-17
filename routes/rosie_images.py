from flask import Blueprint, jsonify, request
import boto3
import json
import os
import requests
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")) if os.environ.get("OPENAI_API_KEY") else None

rekognition = boto3.client(
    "rekognition",
    region_name=os.environ.get("AWS_REGION"),
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
) if all([os.environ.get("AWS_REGION"), os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY")]) else None

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
    try:
        labels_str = ", ".join(labels) if labels else "no labels detected"
        prompt = f"Generate alt text and tooltip text for a real estate image in {neighborhood}. Detected labels: {labels_str}. Image URL: {url}. Return JSON with keys: alt_text, tooltip_text."
        
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
    print("DEBUG: Headers:", dict(request.headers))
    print("DEBUG: Content-Type:", request.content_type)
    print("DEBUG: Raw data:", request.data)
    print("DEBUG: Raw data decoded:", request.data.decode('utf-8') if request.data else "No data")
    
    data = request.get_json(silent=True)
    
    print("DEBUG: Parsed JSON data:", data)
    print("DEBUG: Data type:", type(data))
    
    if data is None:
        print("DEBUG: JSON parsing returned None")
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    deal_id = data.get("deal_id")
    neighborhood = data.get("neighborhood")
    image_urls = data.get("image_urls")
    
    print("DEBUG: deal_id:", deal_id, "type:", type(deal_id))
    print("DEBUG: neighborhood:", neighborhood, "type:", type(neighborhood))
    print("DEBUG: image_urls:", image_urls, "type:", type(image_urls))
    
    if not deal_id or not neighborhood or image_urls is None:
        print("DEBUG: Validation failed - deal_id:", bool(deal_id), "neighborhood:", bool(neighborhood), "image_urls is None:", image_urls is None)
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
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
    
    return jsonify({
        "status": "ok",
        "deal_id": deal_id,
        "neighborhood": neighborhood,
        "image_count": len(image_urls),
        "images": processed
    })
