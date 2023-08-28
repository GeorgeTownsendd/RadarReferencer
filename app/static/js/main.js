function addSquare(lat, lon, sizeInKm, map) {
  const latDelta = sizeInKm / 111;
  const lonDelta = sizeInKm / (111 * Math.cos((Math.PI / 180) * lat));
  const latLngs = [
    [lat + latDelta / 2, lon - lonDelta / 2],
    [lat + latDelta / 2, lon + lonDelta / 2],
    [lat - latDelta / 2, lon + lonDelta / 2],
    [lat - latDelta / 2, lon - lonDelta / 2],
    [lat + latDelta / 2, lon - lonDelta / 2]
  ];
  return L.polygon(latLngs, {color: 'black'}).addTo(map);
}

// Initialize map and fetch GeoJSON data
let mymap = L.map('mapid').setView([-29.0, 134.0], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(mymap);


// Suppress context menu on the map
mymap.on('contextmenu', function(e) {
  e.originalEvent.preventDefault();
});

let selectedMarkers = new Set();
let markerSVG = '';

// Fetch marker SVG
fetch('/static/svg/map-marker.svg')
  .then(response => response.text())
  .then(text => {
    markerSVG = text;

    // Fetch GeoJSON data
    fetch("/get_geojson")
      .then(response => response.json())
      .then(data => {
        data.features.forEach(feature => {
          let lat = feature.properties.lat;
          let lon = feature.properties.lon;

          let radarIcon = L.divIcon({
            className: 'leaflet-div-icon',
            html: colorizeSVG(markerSVG, 'blue'),
            iconSize: [25, 25]
          });

          let marker = L.marker([lat, lon], {icon: radarIcon}).addTo(mymap);
          marker.feature = feature;  // Attach feature data to marker

          let popupContent = '<div>';
          for (const [key, value] of Object.entries(feature.properties)) {
            popupContent += `<strong>${key}</strong>: ${value}<br>`;
          }
          popupContent += '</div>';

          let popup = L.popup().setContent(popupContent);

          // Marker click event
          marker.on('click', function(e) {
            const name = feature.properties.Name;
            let square;
            if (selectedMarkers.has(marker)) {
              selectedMarkers.delete(marker);
              document.getElementById(name).remove();
              marker.setIcon(L.divIcon({
                className: 'leaflet-div-icon',
                html: colorizeSVG(markerSVG, 'blue'),
                iconSize: [25, 25]
              }));
              marker._square.remove();
            } else {
              selectedMarkers.add(marker);
              let listItem = document.createElement('li');
              listItem.id = name;
              listItem.innerText = name;
              document.getElementById("marker-names").appendChild(listItem);
              marker.setIcon(L.divIcon({
                className: 'leaflet-div-icon',
                html: colorizeSVG(markerSVG, 'green'),
                iconSize: [25, 25]
              }));
              square = addSquare(lat, lon, 512, mymap);
              marker._square = square;
            }
            e.originalEvent.preventDefault();
          });


          // Marker contextmenu event
          marker.on('contextmenu', function(e) {
            popup.setLatLng(e.latlng);
            mymap.openPopup(popup);
            e.originalEvent.preventDefault();
          });
        });
      });
  });

function colorizeSVG(svgText, color) {
  return svgText.replace('<svg ', `<svg fill="${color}" `);
}

// Delete Selection Button
document.getElementById("delete-selection").addEventListener("click", function() {
  selectedMarkers.forEach(marker => {
    marker.setIcon(L.divIcon({
      className: 'leaflet-div-icon',
      html: colorizeSVG(markerSVG, 'blue'),
      iconSize: [25, 25]
    }));
    document.getElementById(marker.feature.properties.Name).remove();
    if (marker._square) {
      marker._square.remove();
    }
  });
  selectedMarkers.clear();
});
6

// Export Selection Button
document.getElementById("export-selection").addEventListener("click", function() {
  let exportData = Array.from(selectedMarkers).map(marker => {
    return marker.feature.properties;
  });
  fetch('/export_markers', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(exportData),
  }).then(response => response.json())
    .then(data => {
      console.log('Export successful:', data);
    })
    .catch((error) => {
      console.error('Export failed:', error);
    });
});


