import ftplib
import os
import shutil
import re
from datetime import datetime, timezone, timedelta

import geopandas as gpd
import pandas as pd
from dateutil import tz
from PIL import Image
import time
import numpy as np

FTP_HOST = "ftp2.bom.gov.au"
FTP_USER = "anonymous"
FTP_PASS = ""

ftp = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS)
ftp.encoding = "utf-8"

ftp.cwd('/anon/gen/radar')


def get_latest_images(radar_id='all'):
    global ftp
    ftp.cwd('/anon/gen/radar')

    latest_images = [i for i in ftp.nlst() if 'png' in i]

    if radar_id == 'all':
        return latest_images
    else:
        return [i for i in latest_images if radar_id in i]


def remove_watermark(img_filename, raw_dir='images/radar/{}/raw/', transparent_dir='images/radar/{}/transparent/'):
    radar_id = img_filename.split('.')[0]
    raw_dir = raw_dir.format(radar_id)
    transparent_dir = transparent_dir.format(radar_id)

    if img_filename in os.listdir(transparent_dir):
        print('Watermark already removed!')
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


def load_existing_images(radar_id='all', raw_dir='images/radar/{}/raw/'):
    if radar_id == 'all':
        image_files = []
        radar_dir = '/'.join('images/radar/{}/raw/'.split('/', 2)[:2])
        r_ids = [os.path.join(radar_dir, o) for o in os.listdir(radar_dir) if os.path.isdir(os.path.join(radar_dir,o))]
        print('radars: {}'.format(','.join(r_ids)))

        for r_id in os.listdir('images/radar/'):
            image_files += os.listdir(raw_dir.format(r_id))

    else:
        image_files = os.listdir(raw_dir.format(radar_id))

    images = [f for f in image_files if 'png' in f]

    return images


def save_image_from_ftp(img_filename, raw_dir='images/radar/{}/raw/'):
    radar_id = img_filename.split('.')[0]
    with open(raw_dir.format(radar_id) + img_filename, 'wb') as f:
        ftp.retrbinary('RETR ' + img_filename, f.write)

    print('Filed saved - {}'.format(img_filename))
    remove_watermark(img_filename, raw_dir=raw_dir)
    reference_image(img_filename, raw_dir='images/radar/{}/transparent/')


def check_radar_attribute(radar_id, attribute):
    radar_data = pd.read_csv('data/radars.csv')
    if radar_id in radar_data['radar_id']:
        return radar_data[radar_data['radar_id'] == radar_id][0][attribute]


def get_center_coords(radar_id):
    data = {
        'IDR044': (-32.7297981, 152.0254045),
        'IDR043': (-32.7297981, 152.0254045),
        'IDR042': (-32.7297981, 152.0254045),
        'IDR712': (-33.701, 151.210),
        'IDR713': (-33.701, 151.210),
        'IDR714': (-33.701, 151.210),
        'IDR032': (-34.264, 150.874),
        'IDR033': (-34.264, 150.874),
        'IDR034': (-34.264, 150.874)
    }

    return data[radar_id]


def get_radar_size(radar_id):
    data = {
        'IDR044': 64000,
        'IDR043': 128000,
        'IDR042': 256000,
        'IDR712': 256000,
        'IDR713': 128000,
        'IDR714': 64000, #???
        'IDR032': 256000,
        'IDR033': 128000,
        'IDR034': 64000
    }

    return data[radar_id]


def reference_image(img_filename, raw_dir='images/radar/{}/raw/', referenced_dir='images/radar/{}/referenced/'):
    radar_id = img_filename.split('.')[0]
    center_coords = get_center_coords(radar_id)

    raw_dir = raw_dir.format(radar_id)
    referenced_dir = referenced_dir.format(radar_id)
    new_filename = img_filename[:-4] + '.tiff'

    if new_filename in os.listdir(referenced_dir):
        print('File already referenced!')
    else:
        proj_str = '"+proj=gnom +lat_0={} +lon_0={}"'.format(center_coords[0], center_coords[1])

        s = get_radar_size(radar_id)
        corner_str = '-{} +{} {} -{}'.format(s, s, s, s)

        #print(corner_str)

        os.system('gdal_translate -a_srs {} -a_ullr {} {} tmp/intermediate.tiff > /dev/null'.format(proj_str, corner_str, raw_dir + img_filename))
        os.system('gdalwarp -overwrite -s_srs {} -t_srs EPSG:3112 tmp/intermediate.tiff {} > /dev/null'.format(proj_str, referenced_dir + new_filename))

        print('File referenced ({})'.format(s))


def reference_unreferenced(radar_id, raw_dir='images/radar/{}/raw/', referenced_dir='images/radar/{}/referenced/'):
    for image in load_existing_images(radar_id, raw_dir):
        reference_image(image, raw_dir=raw_dir, referenced_dir=referenced_dir)


def get_timestamp(img_filename, convert_to_timezone=tz.tzlocal()):
    if 'latest' in img_filename:
        return datetime.now(tz=convert_to_timezone) - timedelta(hours=1)
    s = img_filename[img_filename.index('.T.')+3:-4]

    return datetime.strptime(s, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).astimezone(convert_to_timezone)


def monitor_radars(radar_id_list):
    while True:
        for radar in radar_id_list:
            print('Processing: [{}]'.format(radar))
            current_images = get_latest_images(radar_id=radar)
            existing_images = load_existing_images(radar_id=radar)

            saved = 0

            for image in current_images:
                if image not in existing_images:
                    save_image_from_ftp(image)
                    saved += 1

            if saved == 0:
                print('Saved 0 frames. Already up to date!')
            else:
                print('Saved {} new frames'.format(saved))

        time.sleep(60 * 7)


#latest = load_existing_images('IDR044')

#radars = ['IDR032', 'IDR033', 'IDR044', 'IDR044', 'IDR043', 'IDR042', 'IDR712', 'IDR713', 'IDR714']

#monitor_radars(radars)