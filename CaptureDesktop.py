import time 
import cv2
import numpy as np
import ctypes
import mss
import os

from Config import Config

currentDirectory = os.path.dirname(os.path.abspath(__file__))

class CaptureDesktop:

    frame = None
    output_frame = None
    clean_frame = None
    fps = 0
    output_fps = 0
    avg_fps = []
    window_managed = False

    running = False
    capture = None

    def __init__(self):
        self.config = Config(currentDirectory + '/res/config.ini')
        print("CaptureCard initialized.")

    def start(self):
        self.running = True

        # Set the desired frame rate (120 fps)
        monitor_index = self.config.get_setting("capture", "index", 0)
        crop_mode = self.config.get_setting("capture", "crop_mode", "Exact")

        # capture monitor using mss
        self.capture = mss.mss()
        monitor = self.capture.monitors[monitor_index]

        if (crop_mode == "Exact"):
            self.monitor = {
                "top": monitor["top"] + self.config.get_setting("capture", "top_crop", 0),
                "left": monitor["left"] + self.config.get_setting("capture", "left_crop", 0),
                "width": monitor["width"] - self.config.get_setting("capture", "right_crop", 0) - self.config.get_setting("capture", "left_crop", 0),
                "height": monitor["height"] - self.config.get_setting("capture", "bottom_crop", 0) - self.config.get_setting("capture", "top_crop", 0),
                "mon": monitor_index
            }
        else:
            centerX = monitor["left"] + (monitor["width"] / 2)
            centerY = monitor["top"] + (monitor["height"] / 2)
            cropWidth = self.config.get_setting("capture", "center_crop_width", 0)
            cropHeight = self.config.get_setting("capture", "center_crop_height", 0)

            self.monitor = {
                "top": round(centerY - cropHeight),
                "left": round(centerX - cropWidth),
                "width": round(cropWidth * 2),
                "height": round(cropHeight * 2),
                "mon": monitor_index
            }

        self.windowName = "Monitor Capture Stream"
        cv2.namedWindow(self.windowName, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(self.windowName, cv2.WND_PROP_VISIBLE, cv2.WINDOW_FULLSCREEN)
        cv2.resizeWindow(self.windowName, self.monitor["width"], self.monitor["height"])

        # resize window to half the size
        if (round(self.monitor['width']) >= 1280 or round(self.monitor['height']) >= 720):
            cv2.resizeWindow(self.windowName, round(self.monitor["width"] / 2), round(self.monitor["height"] / 2))

        self.capture_frame()

    def stop(self):
        self.running = False
        print("Stopping desktop capture...")
        time.sleep(1)

        self.capture.close()
        cv2.destroyAllWindows()

    def capture_frame(self):
        fps_limit = int(self.config.get_setting('capture', 'fps_limit'))

        while self.running:
            start_time = time.time()

            self.frame = np.array(self.capture.grab(self.monitor))
            self.frame = self.frame[:, :, :3]
        
            self.clean_frame = self.frame.copy()

            # Calculate FPS
            elapsed_time = time.time() - start_time

            try:
                fps = 1.0 / elapsed_time
            except ZeroDivisionError:
                fps = 999

            self.avg_fps.append(fps)

            if (len(self.avg_fps) > 60):
                self.avg_fps.pop(0)

            avg_fps = round(sum(self.avg_fps) / len(self.avg_fps), 2)
            self.output_fps = round(fps, 2)

            # Display FPS on the frame
            #cv2.putText(self.clean_frame, f"Capture FPS: {avg_fps:.0f}", (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            if (self.output_frame is not None):
                cv2.imshow("Monitor Capture Stream", self.output_frame)

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