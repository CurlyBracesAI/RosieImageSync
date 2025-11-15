from flask import Flask
from routes.rosie_images import bp_rosie_images

app = Flask(__name__)

app.register_blueprint(bp_rosie_images)

@app.route('/')
def index():
    return {"message": "ROSIE AGENT E API"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
