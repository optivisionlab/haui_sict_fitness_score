from ultralytics import YOLO


model = YOLO(r"D:\NCKH_Cham_diem_the_duc\yolo11n.pt")

# Export the model to ONNX format
model.export(format="onnx", imgsz=640, dynamic=True, batch=100, device='cpu')  # creates 'yolo11n.onnx'