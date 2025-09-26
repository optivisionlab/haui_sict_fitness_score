import sys, os
sys.path.insert(0, "/u01/quanlm/fitness_tracking/haui_sict_fitness_score")
import onnxruntime as ort
import numpy as np
import cv2
from typing import List, Tuple, Union
import glob
import os
from src.onnx_model.nms import nms_np, xywh2xyxy_np
import torch
import time
from loguru import logger
import matplotlib.pyplot as plt

class YOLO11:
    """
    YOLO11 ONNX object detection class with batch support.
    Assumes the exported ONNX model has NMS enabled.
    """

    def __init__(self, images: Union[np.ndarray, List[np.ndarray]], yolo_session, imgsz=640, conf: float = 0.5, iou: float = 0.5):
        """
        Args:
            images (np.ndarray or list[np.ndarray]): Single or batch of images (HWC) or [(H,W,C), ...]
            yolo_session (onnxruntime.InferenceSession): Loaded ONNX session
            confidence_thres (float): Confidence threshold for filtering detections
        """
        self.images = images if isinstance(images, list) else [images]
        self.session = yolo_session
        self.confidence_thresh = conf
        self.iou_thresh = iou
        self.classes = [
            "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat","traffic light",
            "fire hydrant","stop sign","parking meter","bench","bird","cat","dog","horse","sheep","cow",
            "elephant","bear","zebra","giraffe","backpack","umbrella","handbag","tie","suitcase","frisbee",
            "skis","snowboard","sports ball","kite","baseball bat","baseball glove","skateboard","surfboard",
            "tennis racket","bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
            "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair","couch",
            "potted plant","bed","dining table","toilet","tv","laptop","mouse","remote","keyboard",
            "cell phone","microwave","oven","toaster","sink","refrigerator","book","clock","vase",
            "scissors","teddy bear","hair drier","toothbrush"
        ]
        np.random.seed(42)  # fix seed để màu không đổi giữa các lần chạy
        self.color_palette = np.random.randint(0, 255, size=(len(self.classes), 3))

        # Get input size from ONNX model
        # input_shape = self.session.get_inputs()[0].shape
        self.input_height, self.input_width = imgsz, imgsz

    @staticmethod
    def scale_coords(coords, pad, gain, orig_shape):
        coords[:, [0,2]] -= pad[1]           # Trừ padding bên trái (x) khỏi x1 và x2
        coords[:, [1,3]] -= pad[0]           # Trừ padding trên (y) khỏi y1 và y2
        coords[:, :4] /= gain                 # Chia cho scale factor đã dùng khi resize (hồi về kích thước gốc)
        coords[:, [0,2]] = np.clip(coords[:, [0,2]], 0, orig_shape[1])  # Clamp x1,x2 trong [0,width]
        coords[:, [1,3]] = np.clip(coords[:, [1,3]], 0, orig_shape[0])  # Clamp y1,y2 trong [0,height]
        return coords

    @staticmethod
    def letterbox(img: np.ndarray, new_shape: Tuple[int,int] = (640,640)) -> Tuple[np.ndarray, Tuple[int,int]]:
        """Resize and pad image keeping aspect ratio."""
        shape = img.shape[:2]
        r = min(new_shape[0]/shape[0], new_shape[1]/shape[1])
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1]-new_unpad[0], new_shape[0]-new_unpad[1]
        dw /= 2
        dh /= 2
        img_resized = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        top, bottom = int(round(dh-0.1)), int(round(dh+0.1))
        left, right = int(round(dw-0.1)), int(round(dw+0.1))
        img_padded = cv2.copyMakeBorder(img_resized, top, bottom, left, right,
                                        cv2.BORDER_CONSTANT, value=(114,114,114))
        return img_padded, (top, left)

    def preprocess(self) -> Tuple[np.ndarray, List[Tuple[int,int]]]:
        """
        Preprocess batch of images for ONNX input.

        Returns:
            batch_data (np.ndarray): Shape (B, 3, H, W), dtype=float32
            pads (list of tuple): Padding (top,left) for each image
        """
        batch_data = []
        pads = []
        original_shape = []
        for img in self.images:
            h0, w0 = img.shape[:2]
            original_shape.append((h0, w0))
            img_rgb = img[..., ::-1]  # BGR->RGB
            img_padded, pad = self.letterbox(img_rgb, (self.input_height, self.input_width))
            img_norm = img_padded.astype(np.float32)/255.0
            img_chw = np.transpose(img_norm, (2,0,1))  # HWC -> CHW
            batch_data.append(img_chw)
            pads.append(pad)
        batch_data = np.stack(batch_data, axis=0)  # (B,3,H,W)
        return batch_data, pads, original_shape


    def postprocess(self, outputs: np.ndarray, pads: list, original_shape: list) -> list:
        results = []
        B = outputs.shape[0]

        for b in range(B):
            pad_top, pad_left = pads[b]
            h0, w0 = original_shape[b]
            gain = min(self.input_height/h0, self.input_width/w0)

            out = outputs[b].T  # (N,84)
            boxes = out[:, :4]       # cx,cy,w,h normalized
            cls_probs = out[:, 4:]   # 80 class probs

            cls_ids = np.argmax(cls_probs, axis=1)
            scores = cls_probs[np.arange(cls_probs.shape[0]), cls_ids]

            # lọc theo confidence
            mask = scores >= self.confidence_thresh
            boxes, scores, cls_ids = boxes[mask], scores[mask], cls_ids[mask]

            # convert xywh -> xyxy
            boxes = xywh2xyxy_np(boxes)

            # scale về ảnh gốc
            boxes = self.scale_coords(boxes, (pad_top, pad_left), gain, (h0, w0))

            # NMS
            keep = nms_np(boxes, scores, self.iou_thresh)
            dets = []
            for idx in keep:
                dets.append({
                    "box": boxes[idx].astype(int).tolist(),
                    "score": float(scores[idx]),
                    "class": int(cls_ids[idx])
                })
            results.append(dets)
        return results
    
    def draw_results(images: list[np.ndarray], detections: list[list[dict]], color_palette: np.ndarray, classes: list[str]) -> list[np.ndarray]:
        """
        Draw bounding boxes and labels on batch of images.
        """
        drawn_images = []
        for img, dets in zip(images, detections):
            img_drawn = img.copy()
            for det in dets:
                x1, y1, x2, y2 = det['box']
                cls_id = det['class']
                score = det['score']
                color = tuple(int(c) for c in color_palette[cls_id])
                cv2.rectangle(img_drawn, (x1, y1), (x2, y2), color, 2)
                label = f"{classes[cls_id]}:{score:.2f}"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(img_drawn, (x1, y1 - h), (x1 + w, y1), color, -1)
                cv2.putText(img_drawn, label, (x1, y1-2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)
            drawn_images.append(img_drawn)
        return drawn_images


    def infer(self) -> List[List[dict]]:
        """
        Run inference on batch of images.

        Returns:
            results (list of list): Detection results for each image
        """
        start_time = time.time()
        batch_data, pads, original_shape = self.preprocess()
        logger.info('preprocess_time: {}', time.time() - start_time)
        start_time = time.time()
        input_name = self.session.get_inputs()[0].name
        logger.info('inference_time: {}', time.time() - start_time)
        outputs = self.session.run(None, {input_name: batch_data})
        # For ONNX NMS=false export, output shape is (B,N,6)
        start_time = time.time()
        results = self.postprocess(outputs[0], pads, original_shape)
        logger.info('postprocess_time: {}', time.time() - start_time)
        return results


if __name__ == "__main__":
    # ==== Cấu hình ====
    yolo_path = '/u01/quanlm/fitness_tracking/haui_sict_fitness_score/models/yolo11n.onnx'
    session = ort.InferenceSession(yolo_path, providers=['CPUExecutionProvider'],)
    
    image_folder = "imgs"
    image_paths = glob.glob(os.path.join('/u01/quanlm/fitness_tracking/haui_sict_fitness_score/assets', image_folder, "*.jpg"))
    images = [cv2.imread(p) for p in image_paths]
    model = YOLO11(images, session, conf=0.5, iou=0.5)
    times = []
    for i in range(50):
        start_time = time.time()
        results = model.infer()
        times.append(time.time() - start_time)
        logger.info('time: {}', time.time() - start_time)
    
    plt.plot(times)
    plt.savefig('time.png')
    exit()
    # drawn_images = YOLO11.draw_results(images, results, model.color_palette, model.classes)
    # ==== Lưu ảnh ra folder output ====
    # save_dir = "output"
    # os.makedirs(save_dir, exist_ok=True)
    # for img, path in zip(drawn_images, image_paths):
    #     filename = os.path.basename(path)
    #     save_path = os.path.join(save_dir, filename)
    #     cv2.imwrite(save_path, img)
    #     print(f"Saved: {save_path}")

    # ==== In ra kết quả bbox ====
    for i, dets in enumerate(results):
        print(f"Image {i} ({image_paths[i]}):")
        for det in dets:
            print(det)
    