import requests
import json
import cv2
import numpy as np
from io import BytesIO
from queue import Queue
import threading


def curl_post(url, payload=None, files=None, headers=None, method="POST"):
    """
    Gửi request (POST/PUT) đến một URL với payload, file upload và headers.

    Parameters:
        url (str): Địa chỉ API.
        payload (dict): Dữ liệu form (mặc định None).
        files (list): Danh sách file theo format của requests (mặc định None).
        headers (dict): Header tùy chỉnh (mặc định None).
        method (str): Phương thức HTTP ('POST' hoặc 'PUT').

    Returns:
        Response object: response từ server.
    """
    if headers is None:
        headers = {'accept': 'application/json'}

    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            data=payload,
            files=files
        )
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print('payload: ', payload)
        print(f"Error: {e}")
        return None


def send_tracking_to_api(ids, xyxy_boxes, frame, collection_name="face"):
    """
    Gửi dữ liệu tracking cùng frame ảnh đến API.
    
    Args:
        ids (list): Danh sách ID tracking.
        xyxy_boxes (list): Danh sách bounding boxes (XYXY).
        frame (np.ndarray): Frame ảnh hiện tại.
        collection_name (str): Tên tập dữ liệu (collection).
    """
    if not ids or frame is None:
        print("Không có ID hoặc frame để gửi.")
        return

    # Tạo payload JSON
    tracking_frame = json.dumps({
        'id': ids,
        'bbox': xyxy_boxes
    })

    print('tracking_frame:', tracking_frame)
    payload = {
        'collection_name': collection_name,
        'tracking_frame': tracking_frame,
        'similarity_threshold': 0.25,
    }

    # Encode frame thành ảnh JPEG
    success, encoded_image = cv2.imencode('.jpg', frame)
    if not success:
        print("Không thể encode frame.")
        return

    # Chuyển ảnh thành bytes cho requests
    if not isinstance(encoded_image, np.ndarray):
        encoded_image = np.array(encoded_image)

    files = [
        ('images', ('frame.jpg', encoded_image.tobytes(), 'image/jpeg'))
    ]
    
    # Gửi request
    response = curl_post(
        url='https://5015285cb473.ngrok-free.app/faces/search',  # chỉnh lại URL thực tế
        payload=payload,
        files=files,
        method='POST'
    )
    
    if response:
        print("API response:", response.json())
    else:
        cv2.imwrite('error_frame.jpg', frame)
        print("Gửi API thất bại.")

    return response


def api_worker(frame_queue):
    while True:
        item = frame_queue.get()
        if item is None:
            break
        ids, boxes, frame = item
        send_tracking_to_api(ids, boxes, frame)
        frame_queue.task_done()