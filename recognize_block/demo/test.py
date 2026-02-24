from ultralytics import YOLO
import time
from loguru import logger


model = YOLO('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/models/yolo11n.pt')
start_time = time.time()
print('start_time: ', start_time)
logger.info('start_time: {}', start_time)
model.predict('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets/imgs', conf=0.5, iou=0.5, device=0, batch=1)
print('time: ', time.time()-start_time)
logger.info('time: {}', time.time()-start_time)