import torchvision.models as models
import torch
import torch.nn as nn
from torchvision.transforms import transforms
from PIL import Image
from src.config.depend import resnet_embedding, mtcnn, to_tensor_transform
from typing import Union, List
import numpy as np
from loguru import logger
import os 

def get_embedding(images: Union[Image.Image, List[Image.Image]], verbose=False):
    if isinstance(images, Image.Image):
        images = [images]

    all_faces = []
    face_counts = []  
    for img_idx, image in enumerate(images):
        face_bbox,conf = mtcnn.detect(image)

        if face_bbox is None:
            logger.warning(f"No face detected in image {img_idx}")
            face_counts.append(0)
            continue
        logger.info("Image {} - face_bbox count: {}", img_idx, len(face_bbox))

        faces = []
        for box_idx, box in enumerate(face_bbox):
            face = image.crop(box)
            if verbose:
                logger.info("face_bbox: {}, conf: {}", face_bbox, conf)
                os.makedirs('tmp/debug_img', exist_ok=True)
                face.save(f"tmp/debug_img/img{img_idx}_face{box_idx}.jpg")
            faces.append(face)

        all_faces.extend(faces)
        face_counts.append(len(faces))

    if not all_faces:
        return [None for _ in range(len(images))]

    face_images = torch.stack([to_tensor_transform(face) for face in all_faces])
    all_embeddings = resnet_embedding(face_images)
    result = []
    idx = 0
    for count in face_counts:
        if count == 0:
            result.append(None)
        else:
            result.append(all_embeddings[idx:idx + count])
            idx += count
    return result

if __name__ == "__main__":
    img1 = Image.open('/home/chuhuyhoang/code/haui_sict_fitness_score/tmp/ce4f9595-07ab-4956-bce6-f106b8129feb-17360026626361641762035.webp')
    img2 = Image.open('//home/chuhuyhoang/code/haui_sict_fitness_score/tmp/jakc-4-1150.jpg')
    emb_list = get_embedding(images=[img1, img2], verbose=True)
    for emb in emb_list:
        logger.debug("embedidng shape: {}", emb.shape if emb is not None else None)