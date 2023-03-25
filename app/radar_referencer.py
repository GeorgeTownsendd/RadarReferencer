import ftplib
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
import geopandas as gpd
from dateutil import tz
from PIL import Image
import time
import numpy as np
import shutil

FTP_HOST = "ftp2.bom.gov.au"
FTP_USER = "anonymous"
FTP_PASS = ""

ftp = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS)
ftp.encoding = "utf-8"

ftp.cwd('/anon/gen/radar')


def log_event(event_text, log_indent=0):
    print('[{}]{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '\t' * log_indent, event_text))


def generate_image_identifier(radar_id, image_type):
    image_type_codes = {
        '512km': '1',
        '256km': '2',
        '128km': '3',
        '64km': '4',
    }

    if len(radar_id) == 2 and radar_id.isnumeric():
        radar_id_str = radar_id
    else:
        if radar_id[:3] == 'IDR':
            radar_id = radar_id[3:]
        radar_id_str = str(radar_id).zfill(2)

    return f"IDR{radar_id_str}{image_type_codes[image_type]}"


def generate_imagery_combinations(radar_ids, imagery_types):
    imagery_identifiers = []
    for radar_id in radar_ids:
        for imagery_type in imagery_types:
            imagery_identifiers.append(generate_image_identifier(radar_id, imagery_type))

    return imagery_identifiers


def get_latest_image_list(radar_ids='all', imagery_types='rain', latest_n=1):
    global ftp
    ftp.cwd('/anon/gen/radar')

    if isinstance(radar_ids, list):
        if (isinstance(radar_ids, str) and radar_ids[0] != 'IDR') or isinstance(radar_ids[0], int):
            radar_ids = ['IDR' + str(r_id).zfill(2) for r_id in radar_ids]

    if imagery_types == 'rain':
        imagery_types = ['1', '2', '3', '4']

    current_imagery_index = [i for i in ftp.nlst() if 'png' in i]
    allowed_imageryids = generate_imagery_combinations(radar_ids, imagery_types)
    filtered_images = [image for image in current_imagery_index if (image[:6] in allowed_imageryids and image[-4:] == '.png')]

    limited_images = []
    for relevant_imageryid in allowed_imageryids:
        relevant_images = []
        for i in filtered_images:
            if i[:6] == relevant_imageryid:
                relevant_images.append(i)

        sorted_by_time = sorted(relevant_images, key=lambda x: get_timestamp(x))
        for x in sorted_by_time[:latest_n]:
            limited_images.append(x)

    return limited_images


def remove_watermark(img_filename, raw_dir='images/radar/{}/raw/', transparent_dir='images/radar/{}/transparent/', log_indent=0):
    radar_id = img_filename.split('.')[0]
    raw_dir = raw_dir.format(radar_id)
    transparent_dir = transparent_dir.format(radar_id)

    if not os.path.exists(transparent_dir):
        os.makedirs(transparent_dir)

    if img_filename in os.listdir(transparent_dir):
        log_event('Watermark removal cancelled: already removed from this frame!', log_indent=log_indent)
    else:
        im = Image.open(raw_dir + img_filename)
        im = im.convert('RGBA')
        data = np.array(im)

        for c in ((192, 192, 192), (0, 0, 0)):
            r1, g1, b1 = c  # Original value
            r2, g2, b2, a2 = 255, 255, 255, 0  # Value that we want to replace it with

            red, green, blue, alpha = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
            mask = (red == r1) & (green == g1) & (blue == b1)
            data[:, :, :4][mask] = [r2, g2, b2, a2]

        im = Image.fromarray(data)
        im.save(transparent_dir + img_filename)
        log_event('Watermark removal succeeded', log_indent=log_indent)


def load_existing_images(radar_id='all', image_dir='images/radar/{}/', type='raw'):
    if radar_id == 'all':
        radar_ids = next(os.walk(image_dir[:-3]))[1]

        image_dir = image_dir + type + '/'
        image_files = []

        for r_id in radar_ids:
            image_files += os.listdir(image_dir.format(r_id))
    else:
        image_dir = image_dir.format(radar_id) + type + '/'
        image_files = os.listdir(image_dir)#[image_dir + fn for fn in os.listdir(image_dir)]

    images = [f for f in image_files if np.array([f.endswith(x) for x in ('png', 'tif', 'tiff')]).any()]

    return images


def save_image_from_ftp(img_filename, raw_dir='images/radar/{}/raw/', log_indent=0):
    radar_id = img_filename.split('.')[0]
    radar_path = raw_dir.format(radar_id)
    if not os.path.exists(radar_path):
        os.makedirs(radar_path)
    with open(radar_path + img_filename, 'wb') as f:
        ftp.retrbinary('RETR ' + img_filename, f.write)

    log_event('Download succeeded: {}'.format(img_filename), log_indent=log_indent)
    remove_watermark(img_filename, raw_dir=raw_dir, log_indent=log_indent+1)
    reference_image(img_filename, raw_dir='images/radar/{}/transparent/', log_indent=log_indent+1)


def get_radar_attribute(radar_id, attribute):
    geojson_data = gpd.read_file('app/static/radar_locations.geojson')
    geojson_data['IDR_Name'] = ['IDR' + str(radar_id).zfill(2) for radar_id in geojson_data['Radar_id'].values]
    print(radar_id, [str(x) for x in geojson_data['IDR_Name'].values])
    if radar_id[:5] in geojson_data['IDR_Name'].values:
        return list(geojson_data[geojson_data['IDR_Name'] == radar_id[:5]][attribute])[0]


def get_radar_coords(radar_id):
    coordinates = (get_radar_attribute(radar_id, attribute='lat'), get_radar_attribute(radar_id, attribute='lon'))

    return coordinates


def reference_image(img_filename, raw_dir='images/radar/{}/raw/', referenced_dir='images/radar/{}/referenced/', log_indent=0):
    radar_id = img_filename.split('.')[0]
    center_coords = get_radar_coords(radar_id)

    raw_dir = raw_dir.format(radar_id)
    referenced_dir = referenced_dir.format(radar_id)
    new_filename = img_filename[:-4] + '.tiff'

    if not os.path.exists(referenced_dir):
        os.makedirs(referenced_dir)

    if new_filename in os.listdir(referenced_dir):
        log_event('Reference cancelled: frame already referenced!', log_indent=log_indent)
    else:
        proj_str = '"+proj=gnom +lat_0={} +lon_0={}"'.format(center_coords[0], center_coords[1])

        print(center_coords[0], center_coords[1])

        radar_radius = {1:512000,
                        2:256000,
                        3:128000,
                        4:64000,
        }[int(radar_id[5])]

        corner_str = '-{} +{} {} -{}'.format(radar_radius, radar_radius, radar_radius, radar_radius)

        os.system('gdal_translate -a_srs {} -a_ullr {} {} tmp/intermediate.tiff > /dev/null'.format(proj_str, corner_str, raw_dir + img_filename))
        os.system('gdalwarp -overwrite -s_srs {} -t_srs EPSG:3112 tmp/intermediate.tiff {} > /dev/null'.format(proj_str, referenced_dir + new_filename))

        log_event('Reference succeeded: size={}'.format(radar_radius), log_indent=log_indent)


def reference_unreferenced(radar_id, raw_dir='images/radar/{}/raw/', referenced_dir='images/radar/{}/referenced/'):
    for image in load_existing_images(radar_id, raw_dir):
        reference_image(image, raw_dir=raw_dir, referenced_dir=referenced_dir)


def get_timestamp(img_filename, convert_to_timezone=tz.tzlocal()):
    if 'latest' in img_filename:
        return datetime.now(tz=convert_to_timezone) - timedelta(hours=1)

    s = img_filename[img_filename.index('.T.') + 3:img_filename.find('.png')]

    return datetime.strptime(s, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).astimezone(convert_to_timezone)


def monitor_radars(radar_id_list, log_indent=0):
    while True:
        for r_id in radar_id_list:
            log_event('Checking for new images ({})'.format(r_id), log_indent=log_indent)
            current_images = get_latest_image_list(radar_id=r_id)
            existing_images = load_existing_images(radar_id=r_id)

            images_to_save = []
            for img_filename in current_images:
                if img_filename not in existing_images and 'tmp' not in img_filename:
                    images_to_save.append(img_filename)

            n_saved = len(images_to_save)
            log_event('{} new images found'.format(n_saved), log_indent=log_indent+1)
            for img_filename in images_to_save:
                save_image_from_ftp(img_filename, log_indent=log_indent+1)

            if n_saved == 0:
                log_event('Saved 0 frames from {} selected radars. Already up to date!'.format(n_saved, len(radar_id_list)), log_indent=log_indent+1)
            else:
                log_event('Saved {} frames from radar {}'.format(n_saved, r_id), log_indent=log_indent+1)

        time.sleep(60 * 7)


def find_temporally_similar_images(radar_ids, time_to_match=datetime.utcnow().replace(tzinfo=timezone.utc), referenced_dir='images/radar/{}/referenced/', threshold_seconds=60*6, log_indent=0):
    image_file_list = []
    for r_id in radar_ids:
        radar_images = load_existing_images(r_id, type='referenced')
        radar_timestamps = [get_timestamp(referenced_dir.format(r_id) + f, convert_to_timezone=timezone.utc) for f in radar_images]
        frame_timedeltas = [time_to_match - ts for ts in radar_timestamps]

        zipped_data = zip(radar_images, radar_timestamps, frame_timedeltas)
        zipped_data = sorted(zipped_data, key=lambda x: x[2])
        radar_images, radar_timestamps, frame_timedeltas = zip(*zipped_data)

        if abs(frame_timedeltas[0].seconds) < threshold_seconds:
            log_event('Frame found for radar: {}'.format(r_id))
            image_file_list.append(referenced_dir.format(r_id) + radar_images[0])
        else:
            log_event('Frame not found for radar: {}'.format(r_id))

    return image_file_list


def create_set(image_list, set_name='auto', sets_dir='/run/media/george/Fastdrive/ScriptData/radarreferencer/images/composite/'):
    if set_name == 'auto':
        set_name = image_list[0][image_list[0].index('.T.')+3:image_list[0].rfind('.')]
    dest_dir = sets_dir + set_name
    if os.path.exists(dest_dir):
        print('Set already exists!')

    else:
        os.mkdir(dest_dir)
        for image_filename in image_list:
            shutil.copy(image_filename, dest_dir)


def load_set(set_name, sets_dir='/run/media/george/Fastdrive/ScriptData/radarreferencer/images/composite/'):
    return [sets_dir + set_name + '/' + s for s in os.listdir(sets_dir + set_name)]


#latest = load_existing_images('IDR044')

#radars = ['IDR032']#, 'IDR033', 'IDR044', 'IDR044', 'IDR043', 'IDR042', 'IDR712', 'IDR713', 'IDR714']

#monitor_radars(radars)

#latest = get_latest_images('IDR032')
#save_image_from_ftp(latest[-1])

#x = load_set('202207130834')

#import matplotlib.pyplot as plt
#import rasterio
#from rasterio.plot import show

#for c in x:
#    src = rasterio.open(c)#x[-1])
#    show(src)

#plt.imshow(src)
#plt.show()
