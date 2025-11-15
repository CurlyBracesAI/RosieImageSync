from flask import Blueprint, jsonify

bp_rosie_images = Blueprint("rosie_images", __name__)

@bp_rosie_images.route("/rosie-images", methods=["POST"])
def rosie_images():
    return jsonify({"status": "ready"})
