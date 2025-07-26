from facenet_pytorch import MTCNN, InceptionResnetV1
from src.config.configs import *
from torchvision.transforms import  Compose, Resize, ToTensor


resnet_embedding = InceptionResnetV1(pretrained=RESNET_EMBEDDING_PATH).eval()
mtcnn = MTCNN(**MTCNN_CONFIG)
to_tensor_transform = Compose([
    Resize((224, 224)),  
    ToTensor()
])
