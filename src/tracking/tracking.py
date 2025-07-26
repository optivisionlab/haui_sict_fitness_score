# import
from ultralytics import YOLO
import cv2
from src.engine.engine import convert_xyxy_to_xywh
from src.config.config import BORTSORT_CONFIG, TRACKING_SHOW, TRACKING_STREAM, SAVE_TRACKING, PERSIST_TRACKING
from src.search.curl_api_search import curl_post, send_tracking_to_api
import json
import numpy as np
from src.engine.engine import draw_target


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


def frame_tracking(frame, model, target_class=0, api_call_interval=30):
    """
    Thực hiện tracking trên một frame duy nhất.
    Giả định dùng YOLOv8 + ByteTrack để tracking, từng frame riêng biệt.
    api_call_interval: Khoảng frame để gửi API một lần.
    """
    results = model.track(
        source=frame,
        tracker=BORTSORT_CONFIG,
        persist=PERSIST_TRACKING,

    )
    annotated_frame = frame.copy()

    if results:
        boxes = results[0].boxes
        print(boxes)
        for box in boxes:
            print(f"Box: {box}")
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            track_id = int(box.id[0]) if box.id is not None else -1
            class_id = int(box.cls[0]) if box.cls is not None else -1
            
            # Chỉ vẽ nếu là class mong muốn (ví dụ: người)
            if class_id == target_class:
                draw_target(annotated_frame, track_id=track_id, box=xyxy)

    return annotated_frame


def frame_tracking_callback(frame):
    return frame_tracking(frame, model=YOLO('yolo11n.pt'))





