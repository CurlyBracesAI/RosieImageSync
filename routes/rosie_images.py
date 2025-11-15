from flask import Blueprint, jsonify
import boto3
import os
import requests
from openai import OpenAI

bp_rosie_images = Blueprint("rosie_images", __name__)

@bp_rosie_images.route("/rosie-images", methods=["POST"])
def rosie_images():
    return jsonify({"status": "ready"})
