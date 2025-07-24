# import
from ultralytics import YOLO
import cv2
from src.engine.engine import convert_xyxy_to_xywh
from src.config.config import BORTSORT_CONFIG, TRACKING_SHOW, TRACKING_STREAM, SAVE_TRACKING, PERSIST_TRACKING
from src.search.curl_api_search import curl_post, send_tracking_to_api
import json
import numpy as np


def extract_tracking_info(result, target_class=0):
    """
    Trích xuất thông tin tracking từ 1 frame result.
    Trả về danh sách ID, bbox XYWH, bbox XYXY cho class cụ thể.
    """
    if result.boxes is None:
        return [], [], []

    cls = [int(x) for x in result.boxes.cls.tolist()] if result.boxes.cls is not None else []
    ids = [int(x) for x in result.boxes.id.tolist()] if result.boxes.id is not None else []
    xywh = [[int(v) for v in box] for box in result.boxes.xywh.tolist()] if result.boxes.xywh is not None else []
    xyxy = [[int(v) for v in box] for box in result.boxes.xyxy.tolist()] if result.boxes.xyxy is not None else []


    id_out, xywh_out, xyxy_out = [], [], []
    for cl, id, box_wh, box_xy in zip(cls, ids, xywh, xyxy):
        if int(cl) == target_class:
            id_out.append(id)
            xywh_out.append(box_wh)
            xyxy_out.append(box_xy)
    return id_out, xywh_out, xyxy_out


def tracking_in_frame(source, model, target_class=0, api_call_interval=30):
    """
    Gọi YOLO model tracking và xử lý kết quả theo class mong muốn.
    """
    # Khởi động thread worker gửi API
    # Mô phỏng real-time tracking có xử lý trong tracking do API có thể lâu hơn tracking khiến tụt fps
    frame_count = 0
    tracker = model.track(
        source=source,
        tracker=BORTSORT_CONFIG,
        persist=PERSIST_TRACKING,
        show=TRACKING_SHOW,
        stream=TRACKING_STREAM,
        save=SAVE_TRACKING
    )

    for result in tracker:
        frame_count += 1
        id_list, xywh_list, xyxy_list = extract_tracking_info(result, target_class)
        if not id_list:
            print("Không có đối tượng nào được phát hiện.")
            continue
        print('>>>> CURL API')
        if frame_count % api_call_interval == 0:
            response = send_tracking_to_api(ids=id_list, xyxy_boxes=xyxy_list, 
                                            frame=result.orig_img, collection_name='face')
            print("API response:", response.json() if response else "No response")

        print('>>>> END CURL API')



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
    

def draw_tracking(frame, ids, boxes, fps=None):
    """
    Vẽ bounding box và ID lên frame.
    :param frame: frame ảnh (numpy array)
    :param ids: list các ID đối tượng
    :param boxes: list các bounding box [x1, y1, x2, y2]
    """
    for id, box in zip(ids, boxes):
        x1, y1, x2, y2 = map(int, box)
        # Vẽ rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        # Vẽ ID
        cv2.putText(frame, f'ID: {id}', (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    if fps is not None:
        cv2.putText(frame, f'FPS: {fps:.2f}', (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    return frame






