import cv2
import numpy as np
import json


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


def tlwh_to_xyah(tlwh):
    x, y, w, h = tlwh
    cx = x + w / 2.
    cy = y + h / 2.
    a = w / float(h)
    return np.array([cx, cy, a, h])


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
    

def draw_target(frame, track_id, box, name=None, color=(0, 255, 0), thickness=2):
    """
    Vẽ bounding box và thông tin ID + name lên frame.
    box: [x1, y1, x2, y2] (tọa độ pixel dạng xyxy)
    """
    x1, y1, x2, y2 = map(int, box)

    # Vẽ khung
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    # Chuẩn bị text hiển thị
    if name:
        text = f"ID: {track_id} | {name}"
    else:
        text = f"ID: {track_id}"

    # Vẽ text phía trên box
    cv2.putText(
        frame,
        text,
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2
    )

    return frame


def write_txt(path, data):
    with open(path, 'a', encoding="utf-8-sig") as f:
        for line in data:
            f.write(f"{line}")
        f.write("\n")