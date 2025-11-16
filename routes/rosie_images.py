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
    data = request.get_json(silent=True)
    
    if data is None:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    deal_id = data.get("deal_id")
    neighborhood = data.get("neighborhood")
    image_urls = data.get("image_urls")
    
    if not deal_id or not neighborhood or image_urls is None:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    return jsonify({
        "status": "ready",
        "deal_id": deal_id,
        "neighborhood": neighborhood,
        "image_count": len(image_urls)
    })
