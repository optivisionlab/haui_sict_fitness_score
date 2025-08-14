import cv2
import threading


class CameraSettings:
    def __init__(self, camera_id, width=640, height=480, fps=60):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps

    def apply_settings(self, camera):
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        camera.set(cv2.CAP_PROP_FPS, self.fps)
    

class CameraViewer:
    def __init__(self, camera_id=0, source=0, settings=None, on_frame_callback=None, save_results=False, save_path=None):
        self.camera_id = camera_id
        self.settings = settings if settings else CameraSettings(camera_id)
        self.source = source
        self.camera = cv2.VideoCapture(self.source)
        self.save_results = save_results  # Default to not saving results
        self.save_path = save_path  # Path to save results if needed
        if self.save_results:
            if not self.save_path:
                self.save_path = f"camera_{camera_id}_results.avi"
            fourcc = cv2.VideoWriter_fourcc(*'XVID')

            # ✅ Lấy kích thước thật từ camera thay vì dùng self.settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))

            self.out = cv2.VideoWriter(self.save_path, fourcc, self.settings.fps, (actual_width, actual_height))


        if self.source == 0:
            self.settings.apply_settings(self.camera)
        if not self.camera.isOpened():
            raise Exception(f"Không thể mở camera với ID {camera_id} và source {source}.")

        self.on_frame_callback = on_frame_callback
        self.stop_flag = False
        self.thread = None
        self._lock = threading.Lock()

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.stop_flag = False
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def _run(self):
        window_name = f"Camera {self.camera_id}"
        frame_count = 0
        while not self.stop_flag:
            ret, frame = self.camera.read()
            if not ret:
                print("Không thể đọc frame từ camera.")
                break

            with self._lock:
                if self.on_frame_callback:
                    try:
                        frame = self.on_frame_callback(frame, frame_count)
                    except Exception as e:
                        print(f"Lỗi trong callback: {e}")
            
            cv2.imshow(window_name, frame)
            if self.save_results:
                # Logic to save results can be added here
                self.out.write(frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stop_flag = True
                break

            frame_count += 1
            
        self._safe_cleanup(window_name)

    def stop(self):
        with self._lock:
            self.stop_flag = True
        if self.thread and self.thread.is_alive():
            if threading.current_thread() != self.thread:
                self.thread.join()
        self.thread = None  # Reset lại

    def _safe_cleanup(self, window_name):
        if self.camera.isOpened():
            self.camera.release()
        cv2.destroyWindow(window_name)

    def release_camera(self):
        self.stop()
        self._safe_cleanup(f"Camera {self.camera_id}")
