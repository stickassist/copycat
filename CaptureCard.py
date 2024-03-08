import time 
import cv2
import numpy as np
import ctypes
import os 

from Config import Config

currentDirectory = os.path.dirname(os.path.abspath(__file__))

class CaptureCard:

    frame = None
    output_frame = None
    clean_frame = None
    fps = 0
    avg_fps = []
    output_fps = 0

    running = False
    capture = None
    window_managed = False

    def __init__(self):
        self.config = Config(currentDirectory + '/res/config.ini')
        print("CaptureCard initialized.")

    def start(self):
        self.running = True

        # Set the desired frame rate (120 fps)
        frame_rate = self.config.get_setting('capture', 'frame_rate', 144)
        width, height = self.config.get_setting('capture', 'video_capture_resolution', "1920x1080").split("x")
        capture_card_index = self.config.get_setting("capture", "index", 0)

        # Set the desired capture method
        video_writer = self.config.get_setting("capture", "video_capture_method", "Microsoft Foundation")
        video_write_val = cv2.CAP_MSMF

        if (video_writer == "Direct Show"):
            video_write_val = cv2.CAP_DSHOW

        self.capture = cv2.VideoCapture(capture_card_index, video_write_val)

        # Set the capture card resolution to 1080p
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))

        # Set the capture card frame rate to frame_rate fps
        self.capture.set(cv2.CAP_PROP_FPS, frame_rate)

        if not self.capture.isOpened():
            print("Error: Failed to open the capture card.")
            return False
        
        print("Capture card opened.")

        self.windowName = "Capture Card Stream"
        cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.windowName, cv2.WND_PROP_VISIBLE, cv2.WINDOW_FULLSCREEN)

        # set widow width and height to 1280x720 for previewing
        if (int(width) >= 1920 or int(height) >= 1080):
            cv2.resizeWindow(self.windowName, round(int(width) * 0.9), round(int(height) * 0.9))

        self.capture_frame()

    def stop(self):
        self.running = False
        print("Stopping capture card...")
        time.sleep(1)

        self.capture.release()
        cv2.destroyAllWindows()

    def capture_frame(self):
        fps_limit = int(self.config.get_setting('capture', 'fps_limit'))
        
        while self.capture.isOpened() and self.running:
            start_time = time.time()
        
            ret, self.frame = self.capture.read()

            if not ret:
                print("Error: Failed to capture frame.")
                self.running = False
                return False
            
            self.clean_frame = self.frame.copy()

            # Calculate FPS
            elapsed_time = time.time() - start_time

            try:
                fps = 1.0 / elapsed_time
            except:
                fps = 999

            self.avg_fps.append(fps)
            
            if (len(self.avg_fps) > 60):
                self.avg_fps.pop(0)

            avg_fps = sum(self.avg_fps) / len(self.avg_fps)
            self.output_fps = avg_fps
            
            # Display FPS on the frame
            # cv2.putText(self.output_frame, f"Capture FPS: {avg_fps:.0f}", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            if (self.output_frame is not None):
                cv2.imshow("Capture Card Stream", self.output_frame)

                # Hide window buttons
                if (not self.window_managed):
                    hwnd = cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)
                    hwnd = ctypes.windll.user32.FindWindowW(None, self.windowName)
                    old_style = ctypes.windll.user32.GetWindowLongW(hwnd, -16)
                    new_style = old_style & ~0x00080000 
                    ctypes.windll.user32.SetWindowLongW(hwnd, -16, new_style)
                    self.window_managed = True
            
            cv2.waitKey(1)

            if (fps_limit != 999 and fps > fps_limit):
                time.sleep(round(1 / fps_limit - elapsed_time, 2))

        return False