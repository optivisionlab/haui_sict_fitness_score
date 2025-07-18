import torchvision.models as models
import torch
import torch.nn as nn
from torchvision.transforms import transforms
from PIL import Image
from src.config.depend import resnet_embedding
from typing import Union
import numpy as np

def get_embedding(image: Union[np.array, Image.Image]):
    pass