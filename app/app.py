from flask import Flask, render_template, jsonify, request, Blueprint
import json

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
    return jsonify({"status": "success"})
