from flask import Blueprint, jsonify, request
import boto3
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
