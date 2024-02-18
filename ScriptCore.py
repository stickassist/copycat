from Config import Config
from ControllerMapping import Buttons
import vgamepad.win.vigem_commons as vcom
import numpy as np
import pyttsx3
import threading
import easyocr
import cv2
import subprocess
import os
import pyAesCrypt
import Copycat
import time

import warnings
warnings.filterwarnings("ignore")

currentDirectory = os.path.dirname(os.path.abspath(__file__))

class PrintColors:
    COLOR_BLACK = "black"
    COLOR_RED = "red"
    COLOR_GREEN = "green"
    COLOR_BLUE = "blue"
    COLOR_BOLD_BLACK = "bold-black"
    COLOR_BOLD_RED = "bold-red"
    COLOR_BOLD_GREEN = "bold-green"
    COLOR_BOLD_BLUE = "bold-blue"

class Template:
    controller = None
    config = Config(currentDirectory + "/res/config.ini")
    report = None

    printQueue = []
    settings = None
    sayThread = None
    OCRReader = None
    buttonRemap = {}
    lastMessage = None
    server = None
    lastMessageTime = time.time()

    ds4DpadButtons = [
        vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH,
        vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST,
        vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH,
        vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST,
    ]

    def __init__(self, controller, report, server=None):
        self.controller = controller
        self.report = report
        self.server = server
        self.buttonRemap = {}

        if (self.report.type == 1):
            self.report.buttons &= ~0xF
            self.report.buttons |= 0x8

        Copycat.set_copycat(self)

    def __del__(self):
        self.printQueue = []
        self.settings = None
        self.sayThread = None
        self.OCRReader = None
        self.report = None
        self.controller = None

    def remap_button(self, button_from, button_to):
        mappedFrom = self.map_button(button_from)
        mappedTo = self.map_button(button_to)

        self.buttonRemap[mappedFrom] = mappedTo

    def unmap_button(self, button_from):
        mappedFrom = self.map_button(button_from)

        try:
            del self.buttonRemap[mappedFrom]
        except:
            pass

    def _set_report(self, report):
        self.report = report

    def _set_settings(self, settings):
        self.settings = settings

    def get_setting(self, key):
        return self.settings.get_setting(key, 'value')
    
    def set_setting(self, key, value):
        self.settings.set_setting(key, 'value', value)

    def print_log(self, text, color=PrintColors.COLOR_BLACK, newline=True):
        self.printQueue.append([text, color, newline])

    def map_range(self, value, from_min, from_max, to_min, to_max):
        return np.interp(value, [from_min, from_max], [to_min, to_max]) 
    
    def get_hwid(self):
        return subprocess.check_output('wmic csproduct get uuid').decode().split('\n')[1].strip()
    
    def decrypt_file(self, file, password):
        try:
            pyAesCrypt.decryptFile(file, file.replace('.encrypted', '') + '.decrypted', password)
        except:
            self.add_log("Failed to decrypt file!" + str(file), "red")

    def encrypt_file(self, file, password):
        try:
            pyAesCrypt.encryptFile(file, file.replace('.decrypted', '') + '.encrypted', password)
        except:
            self.add_log("Failed to encrypt file!", "red")

    # Button functions
    def press_button(self, button, skipRemap=False):
        if (self.controller == None):
            return
        
        if (isinstance(button, (int, bytes))):
            mappedButton = button
        else:
            mappedButton = self.map_button(button)

        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[mappedButton]

                if (mappedButton == 98):
                    return self.left_trigger_float(1, True)
                
                if (mappedButton == 99):
                    return self.right_trigger_float(1, True)
                
                return self.press_button(mappedButton, True)
            except:
                pass

        if (mappedButton == 98):
            return self.left_trigger_float(1)
        
        if (mappedButton == 99):
            return self.right_trigger_float(1)
            
        self.controller.press_button(mappedButton)

    def release_button(self, button, skipRemap=False):
        if (self.controller == None):
            return
        
        if (isinstance(button, (int, bytes))):
            mappedButton = button
        else:
            mappedButton = self.map_button(button)

        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[mappedButton]

                if (mappedButton == 98):
                    return self.left_trigger_float(0, True)
                
                if (mappedButton == 99):
                    return self.right_trigger_float(0, True)
                
                return self.release_button(mappedButton, True)
            except:
                pass

        if (mappedButton == 98):
            return self.left_trigger_float(0)
        
        if (mappedButton == 99):
            return self.right_trigger_float(0)
        
        self.controller.release_button(mappedButton)

    def right_trigger_float(self, value, skipRemap=False):
        if (self.controller == None):
            return
        
        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[99]

                if (mappedButton == 98):
                    return self.left_trigger_float(value, True)
                
                if (mappedButton not in [98, 99]):
                    if (value > 0):
                        return self.press_button(mappedButton, True)
                    else:
                        return self.release_button(mappedButton, True)
            except:
                pass
            
        self.controller.right_trigger_float(np.clip(value, 0, 1))

    def left_trigger_float(self, value, skipRemap=False):
        if (self.controller == None):
            return
        
        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[98]

                if (mappedButton == 99):
                    return self.right_trigger_float(value, True)
                
                if (mappedButton not in [98, 99]):
                    if (value > 0):
                        return self.press_button(mappedButton, True)
                    else:
                        return self.release_button(mappedButton, True)
            except:
                pass
        
        self.controller.left_trigger_float(np.clip(value, 0, 1))

    def left_joystick_float(self, x, y):
        if (self.controller == None):
            return
        
        self.controller.left_joystick_float(np.clip(x, -1, 1), np.clip(y, -1, 1))

    def right_joystick_float(self, x, y):
        if (self.controller == None):
            return
        
        self.controller.right_joystick_float(np.clip(x, -1, 1), np.clip(y, -1, 1))
    
    def press_dpad_button(self, button):
        if (self.report == None):
            return
        
        if (self.report.type == 1):
            self.controller.directional_pad(self.map_button(button))
        else:
            self.controller.press_button(self.map_button(button))

    def release_dpad_button(self, button):
        if (self.report == None):
            return
        
        if (self.report.type == 1):
            self.controller.directional_pad(vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)
        else:
            self.controller.release_button(self.map_button(button))

    # Get actual button states from real report
    def is_actual_button_pressed(self, button, skipRemap=False):
        if (self.report == None):
            return False
        
        if (isinstance(button, (int, bytes))):
            mappedButton = button
        else:
            mappedButton = button[self.report.type]

        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[mappedButton]
            except:
                pass

            if (mappedButton == 98):
                return self.get_actual_left_trigger(True) > 0
            
            if (mappedButton == 99):
                return self.get_actual_right_trigger(True) > 0
        
        if (self.report.type == 1 and mappedButton in self.ds4DpadButtons):
            dpad_bits = self.report.buttons & 0xF

            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST):
                return mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH or mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
            
            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST):
                return mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH or mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
            
            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST):
                return mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH or mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
            
            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST):
                return mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH or mappedButton == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST

            return dpad_bits == mappedButton

        return self.report.buttons & mappedButton == mappedButton
    
    def is_actual_special_button_pressed(self, button):
        if (self.report == None):
            return False
        
        if (isinstance(button, (int, bytes))):
            mappedButton = button
        else:
            mappedButton = button[self.report.type]

        if (self.report.type == 0):
            try:
                mappedButton = self.buttonRemap[mappedButton]
            except:
                pass

            return self.report.buttons & mappedButton == mappedButton
    
        return self.report.special & mappedButton == mappedButton

    def get_actual_left_stick_x(self):
        if (self.report == None):
            return 0
        
        return round(self.report.thumbLX, 2)
    
    def get_actual_left_stick_y(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 1):
            return round(-self.report.thumbLY, 2)
        else:
            return round(self.report.thumbLY, 2)
    
    def get_actual_right_stick_x(self):
        if (self.report == None):
            return 0
        
        return round(self.report.thumbRX, 2)
    
    def get_actual_right_stick_y(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 1):
            return round(-self.report.thumbRY, 2)
        else:
            return round(-self.report.thumbRY, 2)
    
    def get_actual_left_trigger(self, skipRemap=False):
        if (self.report == None):
            return 0
        
        mappedButton = 98

        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[mappedButton]
            except:
                pass

        if (mappedButton not in [98, 99]):
                return self.is_actual_button_pressed(mappedButton, True)

        if (mappedButton == 99):
            return self.get_actual_right_trigger(True)

        return round(self.report.leftTrigger, 2)
    
    def get_actual_right_trigger(self, skipRemap=False):
        if (self.report == None):
            return 0
        
        mappedButton = 99

        if (skipRemap == False):
            try:
                mappedButton = self.buttonRemap[mappedButton]
            except:
                pass

        if (mappedButton not in [98, 99]):
            return self.is_actual_button_pressed(mappedButton, True)

        if (mappedButton == 98):
            return self.get_actual_left_trigger(True)
        
        return round(self.report.rightTrigger, 2)
    
    # Get emulated button states from controller report
    def is_emulated_button_pressed(self, button):
        if (self.report == None):
            return False
        
        if (self.report.type == 1 and button[self.report.type] in self.ds4DpadButtons):
            dpad_bits = self.controller.report.wButtons & 0xF

            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST):
                return button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH or button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
            
            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST):
                return button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH or button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST
            
            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST):
                return button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH or button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST
            
            if (dpad_bits == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST):
                return button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH or button[self.report.type] == vcom.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST

            return dpad_bits == button[self.report.type]
        
        return self.controller.report.wButtons & button[self.report.type] == button[self.report.type]
    
    # Get emulated button states from controller report
    def is_emulated_special_button_pressed(self, button):
        if (self.report == None):
            return False
        
        if (self.report.type == 0):
            return self.controller.report.wButtons & button[self.report.type] == button[self.report.type]
        
        return self.controller.report.bSpecial & button[self.report.type] == button[self.report.type]
    
    def get_emulated_left_stick_x(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 0):
            return self.map_range(self.controller.report.sThumbLX, -32768, 32767, -1, 1)
        else:
            return self.map_range(self.controller.report.bThumbLX, 0, 255, -1, 1)
        
    def get_emulated_left_stick_y(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 0):
            return -self.map_range(self.controller.report.sThumbLY, -32768, 32767, -1, 1)
        else:
            return self.map_range(self.controller.report.bThumbLY, 0, 255, -1, 1)
        
    def get_emulated_right_stick_x(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 0):
            return self.map_range(self.controller.report.sThumbRX, -32768, 32767, -1, 1)
        else:
            return self.map_range(self.controller.report.bThumbRX, 0, 255, -1, 1)
        
    def get_emulated_right_stick_y(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 0):
            return -self.map_range(self.controller.report.sThumbRY, -32768, 32767, -1, 1)
        else:
            return self.map_range(self.controller.report.bThumbRY, 0, 255, -1, 1)
        
    def get_emulated_left_trigger(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 0):
            return self.map_range(self.controller.report.bLeftTrigger, 0, 255, 0, 1)
        else:
            return self.map_range(self.controller.report.bTriggerL, 0, 255, 0, 1)
        
    def get_emulated_right_trigger(self):
        if (self.report == None):
            return 0
        
        if (self.report.type == 0):
            return self.map_range(self.controller.report.bRightTrigger, 0, 255, 0, 1)
        else:
            return self.map_range(self.controller.report.bTriggerR, 0, 255, 0, 1)
        
    # General functions
    def map_button(self, button):
        return button[self.report.type]
    
    # Speak functions
    def say(self, text):
        if (self.sayThread != None and self.sayThread.is_alive()):
            return
        
        self.sayThread = threading.Thread(target=self.sayFunc, args=(text,), daemon=True)
        self.sayThread.start()

    def sayFunc(self, text):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        self.sayThread = None

    # Screen reading functions
    def init_ocr(self, languages=['en'], gpu=True):
        # read text from image using easyocr
        if (self.OCRReader == None):
            self.OCRReader = easyocr.Reader(languages, gpu=gpu)

            self.print_log("Initializing OCR", PrintColors.COLOR_BLUE)

            for key, lang in enumerate(languages):
                self.print_log("Loading language: " + lang, PrintColors.COLOR_BLUE)


    def read_text(self, frame, x, y, width, height):
        if (self.OCRReader == None):
            self.init_ocr()
            return []
        
        cropped = frame[y:y+height, x:x+width]

        return self.OCRReader.readtext(cropped, detail=0)
    
    # Image finder
    def search_image(self, haystack, needle, threshold=0.8):

        if len(haystack.shape) == 3:
            haystack = cv2.cvtColor(haystack, cv2.COLOR_BGR2GRAY)

        if len(needle.shape) == 3:
            needle = cv2.cvtColor(needle, cv2.COLOR_BGR2GRAY)

        result= cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val < threshold:
            return None
        
        height, width= needle.shape[:2]

        top_left = max_loc
        bottom_right = (top_left[0] + width, top_left[1] + height)

        return [top_left, bottom_right]