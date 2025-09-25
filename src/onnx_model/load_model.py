import onnxruntime as ort
import numpy as np
import cv2
from typing import List, Tuple, Union
import glob
import os


class YOLO11:
    """
    YOLO11 ONNX object detection class with batch support.
    Assumes the exported ONNX model has NMS enabled.
    """

    def __init__(self, images: Union[np.ndarray, List[np.ndarray]], yolo_session, confidence_thres: float = 0.5):
        """
        Args:
            images (np.ndarray or list[np.ndarray]): Single or batch of images (HWC) or [(H,W,C), ...]
            yolo_session (onnxruntime.InferenceSession): Loaded ONNX session
            confidence_thres (float): Confidence threshold for filtering detections
        """
        self.images = images if isinstance(images, list) else [images]
        self.session = yolo_session
        self.confidence_thres = confidence_thres
        self.classes = ['licence_plate']
        self.color_palette = np.random.uniform(0, 255, size=(len(self.classes), 3))

        # Get input size from ONNX model
        input_shape = self.session.get_inputs()[0].shape
        self.input_height, self.input_width = input_shape[2], input_shape[3]

    @staticmethod
    def letterbox(img: np.ndarray, new_shape: Tuple[int,int] = (640,640)) -> Tuple[np.ndarray, Tuple[int,int]]:
        """Resize and pad image keeping aspect ratio."""
        shape = img.shape[:2]
        r = min(new_shape[0]/shape[0], new_shape[1]/shape[1])
        new_unpad = int(shape[1]*r), int(shape[0]*r)
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
        for img in self.images:
            h0, w0 = img.shape[:2]
            img_rgb = img[..., ::-1]  # BGR->RGB
            img_padded, pad = self.letterbox(img_rgb, (self.input_height, self.input_width))
            img_norm = img_padded.astype(np.float32)/255.0
            img_chw = np.transpose(img_norm, (2,0,1))  # HWC -> CHW
            batch_data.append(img_chw)
            pads.append(pad)
        batch_data = np.stack(batch_data, axis=0)  # (B,3,H,W)
        return batch_data, pads

    def postprocess(self, output: np.ndarray, pads: List[Tuple[int,int]]) -> List[List[dict]]:
        """
        Postprocess ONNX outputs (with NMS already applied).

        Args:
            output (np.ndarray): ONNX output of shape (B, N, 6) [x1,y1,x2,y2,score,class]
            pads (list of tuple): Padding applied to each image

        Returns:
            results (list of list): Each element is a list of dict {box:[x1,y1,x2,y2], score, class}
        """
        results = []
        for i, pad in enumerate(pads):
            pad_top, pad_left = pad
            bboxes = []
            for det in output[i]:
                x1, y1, x2, y2, score, cls = det
                if score < self.confidence_thres:
                    continue
                # Remove padding and scale back to original image
                left = max(int(x1 - pad_left), 0)
                top = max(int(y1 - pad_top), 0)
                right = int(x2 - pad_left)
                bottom = int(y2 - pad_top)
                bboxes.append({"box":[left,top,right,bottom], "score":float(score), "class":int(cls)})
            results.append(bboxes)
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
                color = color_palette[cls_id]
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
        batch_data, pads = self.preprocess()
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: batch_data})
        # For ONNX NMS=true export, output shape is (B,N,6)
        return self.postprocess(outputs[0], pads)


if __name__ == "__main__":
    # ==== Cấu hình ====
    yolo_path = '/u01/quanlm/fitness_tracking/haui_sict_fitness_score/models/yolo11n.onnx'
    session = ort.InferenceSession(yolo_path, providers=['CPUExecutionProvider'])
    
    image_folder = "imgs"
    image_paths = glob.glob(os.path.join('/u01/quanlm/fitness_tracking/haui_sict_fitness_score', image_folder, "*.png"))
    images = [cv2.imread(p) for p in image_paths]
    
    model = YOLO11(images, session, confidence_thres=0.5)
    
    results = model.infer()
    drawn_images = YOLO11.draw_results(images, results, model.color_palette, model.classes)

    # ==== Lưu ảnh ra folder output ====
    save_dir = "output"
    os.makedirs(save_dir, exist_ok=True)
    for img, path in zip(drawn_images, image_paths):
        filename = os.path.basename(path)
        save_path = os.path.join(save_dir, filename)
        cv2.imwrite(save_path, img)
        print(f"Saved: {save_path}")

    # ==== In ra kết quả bbox ====
    for i, dets in enumerate(results):
        print(f"Image {i} ({image_paths[i]}):")
        for det in dets:
            print(det)
    