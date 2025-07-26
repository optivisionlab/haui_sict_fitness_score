import cv2
import numpy as np


def convert_xyxy_to_xywh(box):
    '''
    Convert bounding box from xyxy format to xywh format.
    box: [x1, y1, x2, y2]
    return: [x_center, y_center, width, height]
    '''
    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    x_center = x1 + width / 2
    y_center = y1 + height / 2
    return [x_center, y_center, width, height]


def draw_line_in_frame(frame, ratio_from_bottom=0.3):
    '''
    Vẽ một đường ngang ở tỉ lệ chiều cao từ dưới lên và trả về tọa độ line.

    Parameters:
        frame: numpy array (OpenCV image)
        ratio_from_bottom: float (tỉ lệ chiều cao từ dưới lên, mặc định 0.3)

    Returns:
        frame: Frame đã vẽ line
        line: tuple (x1, y1, x2, y2) tọa độ đường vừa vẽ
    '''
    height, width = frame.shape[:2]

    # Tính y cách đáy ratio% chiều cao
    y = int(height * (1 - ratio_from_bottom))

    # Tọa độ line từ trái sang phải
    line = (0, y, width, y)

    # Vẽ line
    cv2.line(frame, (line[0], line[1]), (line[2], line[3]), (0, 255, 0), 2)

    return frame, line

    
def line_begin_curl_api_search(line, box, mode='xywh'):
    '''
    Function to detect if any bounding box crosses a specified line.
    Returns True if the box crosses the line, False otherwise.
    '''
    if mode == 'xyxy':
        xywh = convert_xyxy_to_xywh(box)
        x_center, y_center, width, height = xywh
    else:
        x_center, y_center, width, height = box

    x1, y1 = line
    if y_center > y1:
        return True
    else:
        return False
    

def draw_target(frame, track_id, box, color=(0, 255, 0), thickness=2):
    '''
    Vẽ bounding box lên frame.
    box: [x1, y1, x2, y2]
    '''
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    cv2.putText(
        frame,
        f"ID: {track_id}",
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 255, 0),
        2
    )
    return frame