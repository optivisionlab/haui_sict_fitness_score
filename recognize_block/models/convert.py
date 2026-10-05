from ultralytics import YOLO

# Load the YOLO11 model
model = YOLO("/u01/quanlm/fitness_tracking/haui_sict_fitness_score/models/yolo11n.pt")

# Export the model to ONNX format
model.export(format="onnx", imgsz=640, nms=False, dynamic=True, device='cpu', half=True)  # creates 'yolo11n.onnx'
