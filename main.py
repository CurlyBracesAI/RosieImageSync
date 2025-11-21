from flask import Flask
from routes.rosie_images import bp_rosie_images
from routes.wix_sync import bp_wix_sync

app = Flask(__name__)

app.register_blueprint(bp_rosie_images)
app.register_blueprint(bp_wix_sync)

@app.route('/')
def index():
    return {"message": "ROSIE AGENT E API"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
