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

@bp.route('/export_markers', methods=['POST'])
def export_markers():
    data = request.json
    print("Exported Markers:", json.dumps(data, indent=4))
    return jsonify({'status': 'success'})