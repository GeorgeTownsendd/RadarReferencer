# RadarReferencer
A set of scripts to automatically download and georeference radar imagery from the Australian Bureau of Meteorology public FTP server.[0]

# Process
Unreferenced .png files are available from the BoM FTP server. The radar maps and imagery use a gnomonic projection [1], thus are simply georeferenced using GDAL. The script outputs .tiff files referenced to EPSG3112, however this can be trivially changed to any CRS.  

# Example
The 64km, 128km, and 256km feeds of the Newcastle (Lemon Tree Passage) and Sydney (Terry Hills) radars combined into a single composite image over a Google Satellite view basemap.  

![Example](example.png?raw=true "Example")


[0] http://www.bom.gov.au/catalogue/anon-ftp.shtml
[1] http://www.bom.gov.au/australia/radar/about/radar_map_features.shtml
