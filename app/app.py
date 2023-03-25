from flask import Flask, render_template, jsonify, request, Blueprint
import json
import app.radar_referencer as rr

bp = Blueprint('app', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/get_geojson')
def get_geojson():
    with open('app/static/radar_locations.geojson', 'r') as f:
        geojson_data = json.load(f)
    return jsonify(geojson_data)


@bp.route('/export_selection', methods=['POST'])
def export_selection():
    selected_features = request.json
    print(selected_features)

    radar_ids = selected_features.keys()
    imagery_types = ['128km']

    images_to_download = rr.get_latest_image_list(radar_ids, imagery_types)

    for image_filename in images_to_download:
        rr.save_image_from_ftp(image_filename)

    return jsonify({"status": "success"})
