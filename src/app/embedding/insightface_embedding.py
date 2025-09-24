from typing import List, Union
from PIL import Image
import numpy as np
import torch
import insightface
from loguru import logger

# Khởi tạo InsightFace chỉ 1 lần ngoài hàm
face_app = insightface.app.FaceAnalysis(
    name="buffalo_l",  # model chính xác cao nhất hiện tại
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
)
# ctx_id = 0 -> GPU, -1 -> CPU
face_app.prepare(ctx_id=0, det_size=(640, 640))


def get_embedding(images: Union[Image.Image, List[Image.Image]], verbose: bool = False):
    """
    Lấy embedding khuôn mặt dùng InsightFace.
    Trả về list theo thứ tự ảnh đầu vào:
        - None nếu không tìm thấy mặt
        - Hoặc torch.Tensor shape (n_faces, 512) nếu có n khuôn mặt.
    """
    if isinstance(images, Image.Image):
        images = [images]

    results: List[Union[None, torch.Tensor]] = []

    for img_idx, image in enumerate(images):
        # PIL -> BGR numpy (InsightFace yêu cầu BGR)
        img_bgr = np.array(image.convert("RGB"))[:, :, ::-1]

        faces = face_app.get(img_bgr)

        if not faces:
            logger.warning(f"No face detected in image {img_idx}")
            results.append(None)
            continue

        # Lấy embedding (InsightFace đã chuẩn hóa L2)
        embs = torch.tensor(
            [f.embedding for f in faces], dtype=torch.float32
        )

        if verbose:
            logger.info("Image {} - face count: {}", img_idx, len(faces))

        results.append(embs)

    return results

if __name__ == "__main__":
    img1 = Image.open('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/Screenshot 2025-06-12 100448.png')
    img2 = Image.open('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/Screenshot 2025-06-12 103845.png')
    emb_list = get_embedding(images=[img1, img2], verbose=True)
    for emb in emb_list:
        logger.debug("embedidng shape: {}", emb.shape if emb is not None else None)