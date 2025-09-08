# import
from ultralytics import YOLO
import cv2
from src.engine.engine import convert_xyxy_to_xywh
from src.config.config import BORTSORT_CONFIG, TRACKING_SHOW, TRACKING_STREAM, SAVE_TRACKING, PERSIST_TRACKING, TRACKING_CONF, TRACKING_IOU
from src.search.curl_api_search import curl_post, send_tracking_to_api
import json
import numpy as np
from src.engine.engine import draw_target
from src.tracking.deep_sort.deep_sort.detection import Detection
from loguru import logger


id_to_name = {}

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
        save=SAVE_TRACKING,
        conf=TRACKING_CONF,
        iou=TRACKING_IOU,
    )

    for result in tracker:
        frame_count += 1
        id_list, xywh_list, xyxy_list = extract_tracking_info(result, target_class)
        if not id_list:
            logger.error("Không có đối tượng nào được phát hiện.")
            continue
        logger.info('>>>> CURL API')

        logger.info('>>>> END CURL API')


def frame_tracking(frame, model, target_class=0, api_call_interval=30, frame_number=0):
    """
    Thực hiện tracking trên một frame duy nhất.
    Giả định dùng YOLOv11 + Bortsort để tracking, từng frame riêng biệt.
    api_call_interval: Khoảng frame để gửi API một lần.
    """
    results = model.track(
        source=frame,
        imgsz=640,
        tracker=BORTSORT_CONFIG,
        persist=PERSIST_TRACKING,
        conf=TRACKING_CONF,
        iou=TRACKING_IOU,
    )
    annotated_frame = frame.copy()

    if results:
        boxes = results[0].boxes
        for box in boxes:
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            # print(f"Tracking ID: {box.id}, BBox: {xyxy}")
            track_id = int(box.id[0]) if box.id is not None else -1
            class_id = int(box.cls[0]) if box.cls is not None else -1
            
            # if frame_number % api_call_interval == 0:
            #     # Gửi tracking thông tin đến API
            #     send_tracking_to_api(class_id, [xyxy], frame)

            # Chỉ vẽ nếu là class mong muốn (ví dụ: người)
            if class_id == target_class:
                draw_target(annotated_frame, track_id=track_id, box=xyxy)
            
    
    return annotated_frame


def deepsort_tracking_in_frame(
        frame, frame_idx, tracking_object, detection_model, 
        encode_model, target_class=0, api_call_interval=500
    ):
    '''
    '''
    global id_to_name
    # detections
    detection_results = detection_model(frame, conf=TRACKING_CONF, iou=TRACKING_IOU, verbose=False)[0]
    boxes, scores = [], []
    ids = []
    xyxy_boxes = []

    for box in detection_results.boxes:
        cls = int(box.cls[0]) if box.cls is not None else -1
        if cls == target_class:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            boxes.append([x1, y1, x2 - x1, y2 - y1])
            scores.append(float(box.conf[0]) if box.conf is not None else 1.0)

    if not boxes:
        tracking_object.predict()
        tracking_object.update([])
        return frame  # Không có đối tượng nào được phát hiện
    
    features = encode_model(frame, boxes)
    detections = [Detection(bbox, score, feature) for bbox, score, feature in zip(boxes, scores, features)]
    # tracking
    tracking_object.predict()
    tracking_object.update(detections)

    annotated_frame = frame.copy()

    for idx, track in enumerate(tracking_object.tracks):
        if not track.is_confirmed() or track.time_since_update > 1:
            continue
        bbox = track.to_tlbr()
        track_id = track.track_id
        xyxy_boxes.append([int(x) for x in bbox])
        ids.append(track_id)
        # draw_target(annotated_frame, track_id=track_id, box=bbox)

    if ids and frame_idx % api_call_interval == 0:
        try:
            logger.info('>>>> Gửi tracking đến API')
            response = send_tracking_to_api(ids, xyxy_boxes, frame)
            logger.info(response)
            if response and response.status_code == 200:
                response_data = response.json()
                api_data = response_data.get('data', {})
                logger.info(api_data)
                for entry in api_data:
                    infor = entry.get("infor")
                    if infor and isinstance(infor, dict):
                        metadata = infor.get("metadata", {})
                        name = metadata.get("name", "")
                    else:
                        name = "Unknown"  # hoặc "Unknown"
                    id_to_name[entry["id"]] = name
                logger.info('id_to_name: ', id_to_name)
            else:
                logger.info(f"Failed to send tracking data: {response.status_code}")
        except Exception as e:
            logger.info(f"Lỗi khi gửi hoặc parse JSON từ API: {e}")
            pass

    for track_id, bbox in zip(ids, xyxy_boxes):
        name = id_to_name.get(track_id, None)
        draw_target(annotated_frame, track_id=track_id, name=name, box=bbox)
    return annotated_frame



def frame_tracking_callback(frame, idx, tracking_object, detection_model, encode_model):
    # return frame_tracking(frame, model=model)
    return deepsort_tracking_in_frame(
        frame=frame,
        frame_idx = idx,
        tracking_object=tracking_object,
        detection_model=detection_model,
        encode_model=encode_model,
    )





