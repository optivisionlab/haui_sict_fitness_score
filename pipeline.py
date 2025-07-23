import cv2
import json
import requests
from src.tracking.tracking import tracking_in_frame
from src.search.curl_api_search import curl_post
from src.tracking.tracking import draw_line_in_frame, line_begin_curl_api_search, draw_tracking
from ultralytics import YOLO
from src.config.config import CAMERA_INDEX, VIDEO_PATH


def video_tracking_and_search(video_path=None, model=None, collection_name='face', input_mode='video'):
    '''
    Hàm này dành cho việc custom tracking trên từng frame khi không dùng YOLO tracking.
    TO DO: làm mượt và tăng fps, tách load camera và video ra ngoài, chạy đa luồng.
    '''
    if input_mode == 'video':
        cap = cv2.VideoCapture(video_path)
    elif input_mode == 'camera':
        cap = cv2.VideoCapture(0)
    else:   
        raise ValueError("input_mode must be 'video' or 'camera'")
    
    if not cap.isOpened():
        raise IOError("Cannot open video source")
    # Lấy thông số video
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Đọc từng frame
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # Tracking trên frame
        print("Processing frame...")
        ids, xywhs, xyxys = tracking_in_frame(frame, model)
        xyxy_boxes_pass = []

        # frame = draw_tracking(frame, ids, xyxys, fps=fps)
        cv2.imshow("Camera", frame)

        # Nếu nhấn phím q thì thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("👋 Thoát.")
            break

        # Encode frame thành file ảnh JPEG
        ret, buf = cv2.imencode('.jpg', frame)
        if not ret:
            print("⚠️ Không thể encode frame.")
            continue
        
        tracking_frame = json.dumps({
            'id': ids,
            'bbox': xyxys,
        })
        payload = {
            'image_urls': ['https://example.com/'],
            'collection_name': collection_name,
            'tracking_frame': tracking_frame
        }

        # Encode frame thành file ảnh JPEG
        ret, buf = cv2.imencode('.jpg', frame)
        if not ret:
            print("⚠️ Không thể encode frame.")
            continue

        # Tạo files cho requests
        files = [
            ('images', ('frame.jpg', buf.tobytes(), 'image/jpeg'))
        ]

        response = curl_post(
            url='http://example.com/api/search',
            payload=payload,
            files=files,
            method='POST'
        )

    cap.release()


def yolo_tracking(video_path=None, model=None, collection_name='face', camera_mode=False):
    if camera_mode:
        ids, xywhs, xyxys = tracking_in_frame(source=CAMERA_INDEX, model=model)
    else:
        ids, xywhs, xyxys = tracking_in_frame(source=VIDEO_PATH, model=model)


if __name__ == "__main__":
    # video_path = 'path_to_your_video.mp4'
    model = YOLO('yolo11n.pt') 
    res = yolo_tracking(model=model, camera_mode=True)
    for r in res:
        print(r)
      # Hoặc 'video' nếu bạn muốn sử dụng video
    # cv2.destroyAllWindows()