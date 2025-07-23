# import
from ultralytics import YOLO
import cv2
from src.engine.engine import convert_xyxy_to_xywh
from src.config.config import BORTSORT_CONFIG, TRACKING_SHOW, TRACKING_STREAM, SAVE_TRACKING, PERSIST_TRACKING


def tracking_in_frame(source, model):
    '''
    Function to perform tracking in a single frame using the YOLO model.
    TO DO: multiple tracking
    frame: input frame from the video or camera
    '''
    ids = []
    xywh_boxes = []
    xyxy_boxes = []

    tracker = model.track(
        source=source,
        tracker=BORTSORT_CONFIG,
        persist=PERSIST_TRACKING,
        show=TRACKING_SHOW,
        stream=TRACKING_STREAM,
        save=SAVE_TRACKING
    )

    for r in tracker:
        if r.boxes is None:
            continue  # Không có object nào được detect

        cls = r.boxes.cls.tolist() if r.boxes.cls is not None else []
        id_list = r.boxes.id.tolist() if r.boxes.id is not None else []
        xywh_list = r.boxes.xywh.tolist() if r.boxes.xywh is not None else []
        xyxy_list = r.boxes.xyxy.tolist() if r.boxes.xyxy is not None else []

        # Lọc theo class (ví dụ chỉ lấy class 0)
        for cl, id, xywh_box, xyxy_box in zip(cls, id_list, xywh_list, xyxy_list):
            if int(cl) == 0:
                ids.append(id)
                xywh_boxes.append(xywh_box)
                xyxy_boxes.append(xyxy_box)

    return (ids, xywh_boxes, xyxy_boxes)

 

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






