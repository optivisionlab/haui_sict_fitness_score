# Config file for the project
# This file contains configuration settings for the application.

import yaml
with open('src/config/config.yml', 'r') as file:
    config = yaml.safe_load(file)

# YOLO tracking configuration
BORTSORT_CONFIG = config.get('YOLO_TRACKING', {}).get('tracker_config', 'src/config/botsort.yaml')
TRACKING_SHOW = config.get('YOLO_TRACKING', {}).get('show_tracking', True)
TRACKING_STREAM = config.get('YOLO_TRACKING', {}).get('stream_tracking', True)
SAVE_TRACKING = config.get('YOLO_TRACKING', {}).get('save_results', False)
PERSIST_TRACKING = config.get('YOLO_TRACKING', {}).get('persist', True)
TRACKING_CONF = config.get('YOLO_TRACKING', {}).get('conf', 0.25)
TRACKING_IOU = config.get('YOLO_TRACKING', {}).get('iou', 0.25)

# Camera settings
CAMERA_INDEX = config.get('INPUT_MODE').get('camera').get('camera_index', 0)
VIDEO_PATH = config.get('INPUT_MODE').get('video').get('video_path', 'abcd.mp4')

SEARCH_API_URL = config.get('SEARCH_API', {}).get('url', 'http://10.100.200.119:8000')
