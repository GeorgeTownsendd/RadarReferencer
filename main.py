import ftplib
import os
from datetime import datetime, timezone, timedelta
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


def log_event(event_text, log_indent=0):
    print('[{}]{} {}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '\t' * log_indent, event_text))


def get_latest_images(radar_id='all'):
    global ftp
    ftp.cwd('/anon/gen/radar')

    latest_images = [i for i in ftp.nlst() if 'png' in i]

    if radar_id == 'all':
        return latest_images
    else:
        return [i for i in latest_images if radar_id in i]


def remove_watermark(img_filename, raw_dir='images/radar/{}/raw/', transparent_dir='images/radar/{}/transparent/', log_indent=0):
    radar_id = img_filename.split('.')[0]
    raw_dir = raw_dir.format(radar_id)
    transparent_dir = transparent_dir.format(radar_id)

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


def load_existing_images(radar_id='all', raw_dir='images/radar/{}/raw/'):
    if radar_id == 'all':
        image_files = []
        radar_dir = '/'.join('images/radar/{}/raw/'.split('/', 2)[:2])
        r_ids = [os.path.join(radar_dir, o) for o in os.listdir(radar_dir) if os.path.isdir(os.path.join(radar_dir,o))]
        #print('radars: {}'.format(','.join(r_ids)))

        for r_id in os.listdir('images/radar/'):
            image_files += os.listdir(raw_dir.format(r_id))

    else:
        image_files = os.listdir(raw_dir.format(radar_id))

    images = [f for f in image_files if 'png' in f]

    return images


def save_image_from_ftp(img_filename, raw_dir='images/radar/{}/raw/', log_indent=0):
    radar_id = img_filename.split('.')[0]
    with open(raw_dir.format(radar_id) + img_filename, 'wb') as f:
        ftp.retrbinary('RETR ' + img_filename, f.write)

    log_event('Download succeeded: {}'.format(img_filename), log_indent=log_indent)
    remove_watermark(img_filename, raw_dir=raw_dir, log_indent=log_indent+1)
    reference_image(img_filename, raw_dir='images/radar/{}/transparent/', log_indent=log_indent+1)


def get_radar_attribute(radar_id, attribute):
    radar_data = pd.read_csv('data/radars.csv')
    if radar_id in radar_data['radar_id'].values:
        return list(radar_data[radar_data['radar_id'] == radar_id][attribute])[0]


def get_radar_coords(radar_id):
    coordinates = (get_radar_attribute(radar_id, attribute='lat'), get_radar_attribute(radar_id, attribute='lon'))

    return coordinates


def reference_image(img_filename, raw_dir='images/radar/{}/raw/', referenced_dir='images/radar/{}/referenced/', log_indent=0):
    radar_id = img_filename.split('.')[0]
    center_coords = get_radar_coords(radar_id)

    raw_dir = raw_dir.format(radar_id)
    referenced_dir = referenced_dir.format(radar_id)
    new_filename = img_filename[:-4] + '.tiff'

    if new_filename in os.listdir(referenced_dir):
        log_event('Reference cancelled: frame already referenced!', log_indent=log_indent)
    else:
        proj_str = '"+proj=gnom +lat_0={} +lon_0={}"'.format(center_coords[0], center_coords[1])

        radar_radius = get_radar_attribute(radar_id, attribute='size')
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
    s = img_filename[img_filename.index('.T.')+3:-4]

    return datetime.strptime(s, '%Y%m%d%H%M').replace(tzinfo=timezone.utc).astimezone(convert_to_timezone)


def monitor_radars(radar_id_list, log_indent=0):
    while True:
        for r_id in radar_id_list:
            log_event('Checking for new images ({})'.format(r_id), log_indent=log_indent)
            current_images = get_latest_images(radar_id=r_id)
            existing_images = load_existing_images(radar_id=r_id)

            images_to_save = []
            for img_filename in current_images:
                if img_filename not in existing_images:
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


def find_temporally_similar_images(radar_ids, time_to_match=datetime.utcnow().replace(tzinfo=timezone.utc), referenced_dir='images/radar/{}/referenced/'):
    image_file_list = []
    for r_id in radar_ids:
        radar_images = load_existing_images(r_id)
        radar_timestamps = [get_timestamp(referenced_dir.format(r_id) + f,convert_to_timezone=timezone.utc) for f in radar_images]
        frame_timedeltas = [ts - time_to_match for ts in radar_timestamps]
        if sorted(frame_timedeltas)[0] < 5:
            pass



#latest = load_existing_images('IDR044')

radars = ['IDR032', 'IDR033', 'IDR044', 'IDR044', 'IDR043', 'IDR042', 'IDR712', 'IDR713', 'IDR714']

monitor_radars(radars)

#latest = get_latest_images('IDR032')
#save_image_from_ftp(latest[-1])