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

def get_embedding(images: Union[Image.Image, List[Image.Image]], verbose=False, emb_by_img= False):
    if isinstance(images, Image.Image):
        images = [images]

    all_faces = []
    face_counts = []  

    for img_idx, image in enumerate(images):
        face_bbox, _ = mtcnn.detect(image)

        if face_bbox is None:
            logger.warning(f"No face detected in image {img_idx}")
            face_counts.append(0)
            continue

        logger.info("Image {} - face_bbox count: {}", img_idx, len(face_bbox))

        faces = []
        for box_idx, box in enumerate(face_bbox):
            face = image.crop(box)
            if verbose:
                os.makedirs('tmp/debug_img', exist_ok=True)
                face.save(f"tmp/debug_img/img{img_idx}_face{box_idx}.jpg")
            faces.append(face)

        all_faces.extend(faces)
        face_counts.append(len(faces))

    if not all_faces:
        return []

    face_images = torch.stack([to_tensor_transform(face) for face in all_faces])
    all_embeddings = resnet_embedding(face_images)

    if emb_by_img:
        embeddings_per_image = []
        idx = 0
        for count in face_counts:
            embeddings_per_image.append(all_embeddings[idx:idx+count])
            idx += count

        return embeddings_per_image

    return all_embeddings


if __name__ == "__main__":
    img = Image.open('/home/chuhuyhoang/code/haui_sict_fitness_score/tmp/jakc-4-1150.jpg')
    logger.debug("embedidng shape: {}", get_embedding(image=img, verbose=True).shape)