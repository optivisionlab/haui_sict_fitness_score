from typing import List, Union
from PIL import Image
import numpy as np
import torch
import insightface
from loguru import logger
import base64
import cv2
import os
from src.app.embedding.align_face import align_face_5pts
import argparse

# from src.config.configs import DEVICE

# Khởi tạo InsightFace chỉ 1 lần ngoài hàm
face_app = insightface.app.FaceAnalysis(
    name="buffalo_l",  # model chính xác cao nhất hiện tại
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
# ctx_id = 0 -> GPU, -1 -> CPU
face_app.prepare(ctx_id=0, det_size=(640, 640))

def cv2_to_b64(img, format=".png"):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    success, buffer = cv2.imencode(format, img_rgb)
    if not success:
        raise ValueError("Image encoding failed")
    b64_string = base64.b64encode(buffer).decode("utf-8")
    return b64_string

def get_embedding(images: Union[Image.Image, List[Image.Image]], verbose=False, return_b64=False):
    """
    Lấy embedding khuôn mặt dùng InsightFace.
    Trả về list theo thứ tự ảnh đầu vào:
        - None nếu không tìm thấy mặt
        - Hoặc torch.Tensor shape (n_faces, 512) nếu có n khuôn mặt.
    """
    if isinstance(images, Image.Image):
        images = [images]

    all_faces_data = []
    face_counts = []
    all_face_bbox = []
    b64_str = []
    
    for img_idx, image in enumerate(images):
        image_rgb = image.convert("RGB")
        img_bgr = np.array(image_rgb)[:, :, ::-1]

        faces = face_app.get(img_bgr)

        if not faces:
            logger.warning(f"No face detected in image {img_idx}")
            face_counts.append(0)
            continue
        
        logger.info("Image {} - face count: {}", img_idx, len(faces))

        for box_idx, face in enumerate(faces):
            all_face_bbox.append(face.bbox)
            
            # Aligned face for debug or b64
            if verbose or return_b64:
                aligned_face = align_face_5pts(np.array(image_rgb), face.kps, img_size=224)
                if verbose:
                    os.makedirs('tmp/debug_img', exist_ok=True)
                    face_pil = Image.fromarray(aligned_face)
                    face_pil.save(f"tmp/debug_img/insight_img{img_idx}_face{box_idx}.jpg")
                
                if return_b64:
                    b64_str.append(cv2_to_b64(aligned_face))
            
            all_faces_data.append(face.embedding)
            
        face_counts.append(len(faces))

    if not all_faces_data:
        return [None for _ in range(len(images))]

    # Convert all embeddings to a single torch tensor
    all_embeddings = torch.tensor(np.array(all_faces_data), dtype=torch.float32)
    
    embedding = []
    box_result = []
    b64_result = []
    idx = 0
    for count in face_counts:
        if count == 0:
            embedding.append(None)
            box_result.append(None)
            if return_b64:
                b64_result.append(None)
        else:
            embedding.append(all_embeddings[idx:idx + count])
            box_result.append(all_face_bbox[idx:idx + count])
            if return_b64:
                b64_result.append(b64_str[idx:idx + count])
            idx += count
    
    if return_b64:
        return embedding, box_result, b64_result

    return embedding, box_result

if __name__ == "__main__":



    try:
        img1 = Image.open("/u01/hoangchu/tmp/ibeta_images_labeled/live/083009ecaa675de475a90f6a78a2e702b08_1.png")
        img2 = Image.open("/u01/hoangchu/tmp/ibeta_images_labeled/live/083009ecaa675de475a90f6a78a2e702b08_2.png")
        emb_list, boxes = get_embedding(images=[img1, img2], verbose=True)
        for emb in emb_list:
            logger.debug("embedding shape: {}", emb.shape if emb is not None else None)
    except Exception as e:
        logger.error(f"Test failed: {e}")