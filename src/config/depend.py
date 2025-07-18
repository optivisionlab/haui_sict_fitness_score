from facenet_pytorch import InceptionResnetV1

resnet_embedding = InceptionResnetV1(pretrained='vggface2').eval()