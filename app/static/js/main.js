var map = L.map('map').setView([-29.0, 134.0], 4);
var greenIcon = new L.Icon({
    iconUrl: 'static/img/marker-icon-2x-green.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

var selectedFeatures = {};

function onMarkerClick(e) {
    var marker = e.target;
    var feature = marker.feature;

    if (marker.options.icon === greenIcon) {
        marker.setIcon(L.Icon.Default.prototype);
        delete selectedFeatures[feature.properties.Radar_id];
    } else {
    marker.setIcon(greenIcon);
    selectedFeatures[feature.properties.Radar_id] = {
        ...feature,
        marker: marker,
    };
}

    updateSelectedMarkers();
}

function updateSelectedMarkers() {
    var container = document.getElementById('markersList');
    container.innerHTML = '';
    var selectedMarkersCount = Object.keys(selectedFeatures).length;

    if (selectedMarkersCount > 0) {
        document.getElementById('selectedMarkersHeading').style.display = 'block';
        document.getElementById('defaultText').style.display = 'none';

        for (var radar_id in selectedFeatures) {
            var feature = selectedFeatures[radar_id];
            var div = document.createElement('div');
            div.textContent = feature.properties.Name;
            container.appendChild(div);
        }
    } else {
        document.getElementById('selectedMarkersHeading').style.display = 'none';
        document.getElementById('defaultText').style.display = 'block';
    }
}

function loadGeoJSON(geojson_data) {
    L.geoJSON(geojson_data, {
        onEachFeature: function (feature, layer) {
            layer.on('click', onMarkerClick);
        }
    }).addTo(map);
}

function exportSelection() {
    var exportData = {};

    for (var radar_id in selectedFeatures) {
        exportData[radar_id] = {...selectedFeatures[radar_id]};
        delete exportData[radar_id].marker;
    }

    $.ajax({
        url: '/export_selection',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(exportData),
        success: function (response) {
            if (response.status !== 'success') {
                console.error('Error exporting selection!');
            }
        },
        error: function () {
            console.error('Error exporting selection!');
        }
    });
}


function resetSelection() {
for (var radar_id in selectedFeatures) {
var marker = selectedFeatures[radar_id].marker;
marker.setIcon(L.Icon.Default.prototype);
}
selectedFeatures = {};
updateSelectedMarkers();
}

// Load GeoJSON data from server
$.getJSON('/get_geojson', function (data) {
loadGeoJSON(data);
});

document.getElementById('exportButton').addEventListener('click', exportSelection);
document.getElementById('resetButton').addEventListener('click', resetSelection);