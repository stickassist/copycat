import os
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog
import importlib.util
import threading
import time
import requests
import subprocess
import sys
import pyAesCrypt
import psutil
import shutil
from functools import partial

from PIL import ImageTk, Image
from tkinter import messagebox

from Config import Config
from CaptureCard import CaptureCard
from CaptureDesktop import CaptureDesktop
from Controller import Controller
from ControllerMapping import Buttons

import win32com.client

currentDirectory = os.path.dirname(os.path.abspath(__file__))

# get directories only inside relative folder to current script
def get_directories(relative_path):
    script_path = os.path.dirname(os.path.abspath(__file__))

    target_dir = os.path.join(script_path, relative_path)

    # Check if the directory exists
    if not os.path.isdir(target_dir):
        raise ValueError(f"The directory '{relative_path}' does not exist in the relative script path.")

    # Get the folder names inside the directory
    folder_names = [name for name in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, name))]
    return folder_names

class MonitorBtnPositions:
    BTN_TOUCHPAD = [237, 120]
    BTN_GUIDE = [237, 147]
    BTN_SOUTH = [323, 160]
    BTN_EAST = [337, 145]
    BTN_WEST = [308, 145]
    BTN_NORTH = [323, 131]
    BTN_LEFT_SHOULDER = [166, 72]
    BTN_RIGHT_SHOULDER = [308, 72]
    BTN_BACK = [208, 147]
    BTN_OPTIONS = [267, 147]
    BTN_LEFT_THUMB = [151, 146]
    BTN_RIGHT_THUMB = [282, 207]
    BTN_DPAD_UP = [193, 193]
    BTN_DPAD_DOWN = [193, 222]
    BTN_DPAD_LEFT = [179, 207]
    BTN_DPAD_RIGHT = [208, 207]
    BTN_LEFT_TRIGGER = [171, 36]
    BTN_RIGHT_TRIGGER = [302, 36]

class Encryptor:
    def __init__(self, file_path):
        if not os.path.exists(file_path):
            raise Exception('{} does not exists!'.format(file_path))
        
        self.file_path = file_path
        self.file_name = os.path.basename(self.file_path)
        self.file_dir = os.path.dirname(self.file_path)
        self.file_base_name, self.file_extension = os.path.splitext(self.file_name)

        if not self.file_extension == '.py':
            raise Exception('{} is not .py format!'.format(self.file_extension))
        
        # Creating .pvx file
        self.file_pyx_name = self.file_base_name + '.pyx'

        shutil.copy(self.file_path, self.file_pyx_name)
        self.setup_file()
        self.encrypt()

    def setup_file(self):
        with open('setup.py', '+w') as file:
            file.write("from distutils.core import setup\n"
                       "from Cython.Build import cythonize\n\n"
                       "setup(ext_modules=cythonize('{}'))".format(self.file_pyx_name))

    def encrypt(self):
        command = 'python setup.py build_ext --inplace'
        os.system(str(command))

        pyd_path = self.file_base_name + '.cp38-win_amd64.pyd'
        c_path = self.file_base_name + '.c'

        shutil.copy(pyd_path, self.file_dir)
        os.remove(pyd_path)
        os.remove(self.file_pyx_name)
        os.remove(c_path)
        os.remove('setup.py')

class ScrollableFrame(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)

        # Create a canvas and a scrollbar
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind('<Configure>', self.update_canvas_width)

        # Use a frame to place inside the canvas
        self.inner_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
        self.inner_frame.bind('<Configure>', self.update_scrollregion)

    def update_scrollregion(self, event):
        """ Update the scroll region based on the size of the inner frame """
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    def update_canvas_width(self, event):
        """ Adjust the canvas's width to fill its parent frame """
        width = self.winfo_width()
        self.canvas.itemconfig(self.canvas.create_window((0, 0), window=self.inner_frame, anchor='nw'),
                               width=width)

class Gui:
    version = "0.3.8"
    root = None
    config = Config("res/config.ini")
    output_log = None

    script_thread = None
    capture_thread = None

    capture_method = None
    script_running = False

    hiddenDevices = []

    controller_reader = {}
    controllerInstance = 0

    def hid_hider_command(self, command):
        if (self.config.get_setting('auto_hide', 'enabled', True)):
            if (os.path.exists(self.hidhide_cli_path)):
                self.kill_process_by_name("hidhideclient.exe")
                subprocess.Popen(command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def __init__(self):
        self.root = tk.Tk()

        program_files = os.getenv('PROGRAMFILES')
        self.hidhide_cli_path = program_files + "\\Nefarius Software Solutions\\HidHide\\x64\\HidHideCLI.exe"
        self.hidhide_client_path = program_files + "\\Nefarius Software Solutions\\HidHide\\x64\\HidHideClient.exe"

        # check if file exists
        if (not os.path.exists(self.hidhide_cli_path) and not os.path.exists(self.hidhide_client_path)):
            messagebox.showerror("Error", "HidHideCLI.exe not found on this machine, please install HidHide.")
            script_path = os.path.dirname(os.path.abspath(__file__))
            subprocess.Popen([script_path + '/res/installers/HidHide_1.2.98_x64.exe'])
            os._exit(0)

        # run an .exe file with parameters
        drive = os.path.splitdrive(os.getcwd())[0]
        gpuEnvPath = drive.upper() + "\\tools\\miniconda3\\envs\\gpu\\python.exe"

        # Add python path to hidhider
        command = '"' + self.hidhide_cli_path + '" --app-reg "' + gpuEnvPath + '"'
        self.hid_hider_command(command)

        # enable hiding
        command = '"' + self.hidhide_cli_path + '" --cloak-on'
        self.hid_hider_command(command)

        self.root.tk.call("source", currentDirectory + "/res/azure.tcl")
        self.root.tk.call("set_theme", "light")

        self.root.title("Copycat v" + str(self.version))
        self.root.iconbitmap(currentDirectory + "/res/icons/app.ico")
        self.root.geometry("510x710")

        # disable resize
        self.root.resizable(0, 0)

        # disable fullscreen
        self.root.attributes("-fullscreen", False)
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        app_data_path = os.path.join(os.getenv('APPDATA'), 'Copycat')

        if (os.path.exists(app_data_path) == False):
            os.mkdir(app_data_path)

        self.create_widgets()

    def close_app(self):
        if (self.script_running):
            self.stop()

        self.root.destroy()

    def run_script(self):
        videoMode = self.config.get_setting("capture", "type", "None")
        
        try:
            if (self.moduleInstance == None or self.script_running == False):
                return 
            
            if (self.controller_reader[self.controllerInstance].state == 0):
                return
            
            start_time = time.time()

            # run script loop
            if(videoMode != "None"):
                frame = self.moduleInstance.run(self.capture_method.clean_frame)
                self.capture_method.output_frame = frame
            else:
                self.moduleInstance.run(None)

            if (self.controller_reader[self.controllerInstance].emulated_controller != None):
                self.controller_reader[self.controllerInstance].emulated_controller.update()

            # print log messages
            if (len(self.moduleInstance.printQueue) > 0):
                for message in self.moduleInstance.printQueue:
                    self.add_log(str(message[0]), message[1], message[2])

                self.moduleInstance.printQueue = []

            # Calculate FPS
            elapsed_time = time.time() - start_time

            try:
                fps = 1.0 / elapsed_time
            except ZeroDivisionError:
                fps = 999

            if (fps > 999):
                fps = 999

            self.status_bar_left_label.config(text="Status: Running (" + str(round(fps)) + " Script FPS)")

            if (self.script_running):
                self.root.after(1, self.run_script)
                self.root.after(5, self.update_monitor)
            else:
                self.add_log("Script stopped.", "red")

        except Exception as e:
            # get line of code
            line = sys.exc_info()[-1].tb_lineno
            self.add_log("Script crashed: " + str(e) + ' Line:' + str(line), "red")
            self.stop(True)
    

    def update_monitor(self):
        # reset image in canvas and add monitor image
        self.device_monitor_canvas.delete("all")
        self.device_monitor_canvas.create_image(0, 0, image=self.device_monitor_template, anchor="nw")

        btnSize = 5

        if (self.moduleInstance == None or self.script_running == False):
            return 

        if (self.moduleInstance.is_emulated_special_button_pressed(Buttons.BTN_GUIDE)):
            btnX = MonitorBtnPositions.BTN_GUIDE[0]
            btnY = MonitorBtnPositions.BTN_GUIDE[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_special_button_pressed(Buttons.BTN_TOUCHPAD)):
            btnX = MonitorBtnPositions.BTN_TOUCHPAD[0]
            btnY = MonitorBtnPositions.BTN_TOUCHPAD[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_SOUTH)):
            btnX = MonitorBtnPositions.BTN_SOUTH[0]
            btnY = MonitorBtnPositions.BTN_SOUTH[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_EAST)):
            btnX = MonitorBtnPositions.BTN_EAST[0]
            btnY = MonitorBtnPositions.BTN_EAST[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_WEST)):
            btnX = MonitorBtnPositions.BTN_WEST[0]
            btnY = MonitorBtnPositions.BTN_WEST[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_NORTH)):
            btnX = MonitorBtnPositions.BTN_NORTH[0]
            btnY = MonitorBtnPositions.BTN_NORTH[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_LEFT_SHOULDER)):
            btnX = MonitorBtnPositions.BTN_LEFT_SHOULDER[0]
            btnY = MonitorBtnPositions.BTN_LEFT_SHOULDER[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_RIGHT_SHOULDER)):
            btnX = MonitorBtnPositions.BTN_RIGHT_SHOULDER[0]
            btnY = MonitorBtnPositions.BTN_RIGHT_SHOULDER[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_BACK)):
            btnX = MonitorBtnPositions.BTN_BACK[0]
            btnY = MonitorBtnPositions.BTN_BACK[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_OPTIONS)):
            btnX = MonitorBtnPositions.BTN_OPTIONS[0]
            btnY = MonitorBtnPositions.BTN_OPTIONS[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_LEFT_THUMB)):
            btnX = MonitorBtnPositions.BTN_LEFT_THUMB[0]
            btnY = MonitorBtnPositions.BTN_LEFT_THUMB[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_RIGHT_THUMB)):
            btnX = MonitorBtnPositions.BTN_RIGHT_THUMB[0]
            btnY = MonitorBtnPositions.BTN_RIGHT_THUMB[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_DPAD_UP)):
            btnX = MonitorBtnPositions.BTN_DPAD_UP[0]
            btnY = MonitorBtnPositions.BTN_DPAD_UP[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_DPAD_DOWN)):
            btnX = MonitorBtnPositions.BTN_DPAD_DOWN[0]
            btnY = MonitorBtnPositions.BTN_DPAD_DOWN[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_DPAD_LEFT)):
            btnX = MonitorBtnPositions.BTN_DPAD_LEFT[0]
            btnY = MonitorBtnPositions.BTN_DPAD_LEFT[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        if (self.moduleInstance.is_emulated_button_pressed(Buttons.BTN_DPAD_RIGHT)):
            btnX = MonitorBtnPositions.BTN_DPAD_RIGHT[0]
            btnY = MonitorBtnPositions.BTN_DPAD_RIGHT[1]
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        leftTrigger = self.moduleInstance.get_emulated_left_trigger()
        btnX = MonitorBtnPositions.BTN_LEFT_TRIGGER[0]
        btnY = MonitorBtnPositions.BTN_LEFT_TRIGGER[1]
        if (leftTrigger > 0):
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")

        self.device_monitor_canvas.create_text(btnX + 20, btnY, text=round(leftTrigger, 2), fill="red", anchor="w", tags="red_dot")

        rightTrigger = self.moduleInstance.get_emulated_right_trigger()
        btnX = MonitorBtnPositions.BTN_RIGHT_TRIGGER[0]
        btnY = MonitorBtnPositions.BTN_RIGHT_TRIGGER[1]
        if (rightTrigger > 0):
            self.device_monitor_canvas.create_oval(btnX - btnSize, btnY - btnSize, btnX + btnSize, btnY+btnSize, fill="red", outline="red", tags="red_dot")
            
        self.device_monitor_canvas.create_text(btnX + 20, btnY, text=round(rightTrigger, 2), fill="red", anchor="w", tags="red_dot")

        leftStickX = self.moduleInstance.get_emulated_left_stick_x()
        leftStickY = self.moduleInstance.get_emulated_left_stick_y()
        btnX = MonitorBtnPositions.BTN_LEFT_THUMB[0]
        btnY = MonitorBtnPositions.BTN_LEFT_THUMB[1]
        if (abs(leftStickX) >= 0.01 or abs(leftStickY) >= 0.01):
            self.device_monitor_canvas.create_line(btnX, btnY, btnX + (leftStickX * 20), btnY + (leftStickY * 20), fill="blue", width=2, tags="blue_dot")

        self.device_monitor_canvas.create_text(btnX - 45, btnY + 40, text=("x: " + str(round(leftStickX, 2))), fill="blue", anchor="w", tags="blue_dot")
        self.device_monitor_canvas.create_text(btnX - 45, btnY + 55, text=("y: " + str(round(leftStickY, 2))), fill="blue", anchor="w", tags="blue_dot")

        rightStickX = self.moduleInstance.get_emulated_right_stick_x()
        rightStickY = self.moduleInstance.get_emulated_right_stick_y()
        btnX = MonitorBtnPositions.BTN_RIGHT_THUMB[0]
        btnY = MonitorBtnPositions.BTN_RIGHT_THUMB[1]
        if (abs(rightStickX) >= 0.01 or abs(rightStickY) >= 0.01):
            self.device_monitor_canvas.create_line(btnX, btnY, btnX + (rightStickX * 20), btnY + (rightStickY * 20), fill="blue", width=2, tags="blue_dot")

        self.device_monitor_canvas.create_text(btnX + 35, btnY + 20, text=("x: " + str(round(rightStickX, 2))), fill="blue", anchor="w", tags="blue_dot")
        self.device_monitor_canvas.create_text(btnX + 35, btnY + 35, text=("y: " + str(round(rightStickY, 2))), fill="blue", anchor="w", tags="blue_dot")

        self.root.update_idletasks()
    

    def load_settings_window(self):
        moduleName = self.config.get_setting("script", "name", "None")
        currentDirectory = os.path.dirname(os.path.abspath(__file__))

        if (self.moduleInstance != None):
            # check if settings.ini file exists inside script folder
            if (os.path.isfile(os.path.dirname(os.path.abspath(__file__)) + f"\\scripts\\{moduleName}\\settings.ini")):
                self.script_settings = Config(os.path.dirname(os.path.abspath(__file__)) + f"\\scripts\\{moduleName}\\settings.ini")
                self.moduleInstance._set_settings(self.script_settings)

                # create top level toolwindow that cannot be closed, minimized or maximized
                self.script_settings_window = tk.Toplevel(self.root)
                self.center_window(self.script_settings_window)

                self.script_settings_window.title(moduleName + " Settings")
                self.script_settings_window.iconbitmap(currentDirectory + "/res/icons/app.ico")
                self.script_settings_window.wm_attributes("-toolwindow", True)
                self.script_settings_window.attributes("-topmost", 1)
                self.script_settings_window.protocol("WM_DELETE_WINDOW", lambda: None)
                self.script_settings_window.geometry("350x400")
                self.script_settings_window.resizable(False, True)

                scroll_frame = ScrollableFrame(self.script_settings_window)
                scroll_frame.pack(fill=tk.BOTH, expand=True)
                scroll_frame.inner_frame.grid_columnconfigure(0, weight=1)
                scroll_frame.inner_frame.grid_columnconfigure(1, weight=1)

                row = 0
                for section in self.script_settings.get_sections():
                    field_info = self.script_settings.config[section]
                    
                    if (field_info['type'] == 'onoff'):
                        onoff_label = ttk.Label(scroll_frame.inner_frame, text=field_info['label'])
                        onoff_label.grid(row=row, column=0, columnspan=2, padx=(5, 22), pady=(5, 0), sticky="we")
                        
                        onoff_combo = ttk.Combobox(scroll_frame.inner_frame, values=["Disabled", "Enabled"], state="readonly")
                        onoff_combo.grid(row=row+1, column=0, columnspan=2, padx=(5, 22), pady=(5, 5), sticky="we")

                        onoff_combo.config_target = [field_info['type'], section, 'value']
                        onoff_combo.bind("<<ComboboxSelected>>", self.update_script_setting)

                        if (self.script_settings.get_setting(section, 'value', field_info['default']) == True):
                            onoff_combo.set("Enabled")
                        else:
                            onoff_combo.set("Disabled")

                        row += 2

                    if (field_info['type'] == 'slider'):
                        # Create Slider
                        slider_label = ttk.Label(scroll_frame.inner_frame, text=field_info['label'])
                        slider_label.grid(row=row, column=0, columnspan=2, padx=(5, 22), pady=(5, 0), sticky="we")

                        slider = tk.Scale(scroll_frame.inner_frame, from_=field_info['min'], to=field_info['max'], orient=tk.HORIZONTAL)
                        slider.grid(row=row+1, column=0, padx=(5, 0), pady=(5, 5), sticky="we")

                        slider.config(resolution=round(float(field_info['step']), 2))

                        slider.config_target = [field_info['type'], section, 'value']
                        slider.set(self.script_settings.get_setting(section, 'value', field_info['default']))

                        # Create Entry
                        entry = ttk.Entry(scroll_frame.inner_frame, width=10)
                        entry.grid(row=row+1, column=1, padx=(5, 22), pady=(5, 5), sticky="we")
                        entry.insert(0, str(slider.get()))

                        # Bind Slider and Entry
                        entry.bind("<KeyRelease>", partial(self.update_value_from_entry, entry, slider, field_info, section))
                        slider.bind("<ButtonRelease-1>", partial(self.update_slider_setting, entry, slider, field_info))

                        row += 2

                    if (field_info['type'] == 'label'):
                        label = ttk.Label(scroll_frame.inner_frame, text=field_info['label'], wraplength=(350-22))
                        label.grid(row=row, column=0, columnspan=2, padx=(5, 22), pady=(5, 0), sticky="we")

                        try:
                            label.config(foreground=field_info['color'], background=field_info['bg'])
                        except:
                            try:
                                label.config(foreground=field_info['color'])
                            except:
                                pass

                        row += 1

                    if (field_info['type'] == 'dropdown'):
                        dropdown_label = ttk.Label(scroll_frame.inner_frame, text=field_info['label'])
                        dropdown_label.grid(row=row, column=0, columnspan=2, padx=(5, 22), pady=(5, 0), sticky="we")

                        dropdown = ttk.Combobox(scroll_frame.inner_frame, values=field_info['options'].split(', '), state="readonly")
                        dropdown.grid(row=row+1, column=0, columnspan=2, padx=(5, 22), pady=(5, 5), sticky="we")

                        dropdown.config_target = [field_info['type'], section, 'value']
                        dropdown.bind("<<ComboboxSelected>>", self.update_script_setting)
                        dropdown.set(self.script_settings.get_setting(section, 'value', field_info['default']))

                        row += 2

                    if (field_info['type'] == 'filelister'):
                        currentDirectory = os.path.dirname(os.path.abspath(__file__))
                        folderPath = field_info['path'].replace('/', '\\').strip('\\').strip('"').strip("'")
                        fullpath = currentDirectory + '\\scripts\\' + self.config.get_setting("script", "name", "None") + '\\' + folderPath
                        extensions = field_info['ext'].split(', ')

                        files = []
                        for file in os.listdir(fullpath):
                            if (file.endswith(tuple(extensions))):
                                files.append(file)

                        dropdown_label = ttk.Label(scroll_frame.inner_frame, text=field_info['label'])
                        dropdown_label.grid(row=row, column=0, columnspan=2, padx=(5, 22), pady=(5, 0), sticky="we")

                        dropdown = ttk.Combobox(scroll_frame.inner_frame, values=files, state="readonly")
                        dropdown.grid(row=row+1, column=0, columnspan=2, padx=(5, 22), pady=(5, 5), sticky="we")

                        dropdown.config_target = [field_info['type'], section, 'value']
                        dropdown.bind("<<ComboboxSelected>>", self.update_script_setting)
                        dropdown.set(self.script_settings.get_setting(section, 'value', field_info['default']))

                        row += 2


    def start(self, event):
        self.start_button.config(state="disabled")

        if (event.widget["text"] == "Stop"):
            self.stop()        
            return
        
        videoMode = self.config.get_setting("capture", "type", "None")
        controllerType = self.config.get_setting("input", "device_type", "Xbox Controller")

        strComputer = "."
        objWMIService = win32com.client.Dispatch("WbemScripting.SWbemLocator")
        objSWbemServices = objWMIService.ConnectServer(strComputer, "root\cimv2")
        colItems = objSWbemServices.ExecQuery("SELECT * FROM Win32_PnPEntity")
        self.hiddenDevices = []

        currentDirectory = os.path.dirname(os.path.abspath(__file__))

        if (self.config.get_setting('auto_hide', 'enabled', True)):
            controllerNames = [
                "Xbox Controller",
                "Xbox One Controller",
                "Xbox Wireless Controller",
                "Xbox Gaming Device",
                "Wireless Controller",
                "Game Controller",
                "Xbox",
                "Duelsense"
            ]

            if (os.path.exists(currentDirectory + "/res/devices.txt")):
                self.add_log("Resetting previous hide states...")

                with open(currentDirectory + "/res/devices.txt", "r") as file:
                    for line in file:
                        command = '"' + self.hidhide_cli_path + '" --dev-unhide "' + line.strip() + '"'
                        self.hid_hider_command(command)

            for objItem in colItems:
                for controllerName in controllerNames:
                    if objItem.Name and controllerName.lower() in objItem.Name.lower():
                        command = '"' + self.hidhide_cli_path + '" --dev-hide "' + str(objItem.DeviceID) + '"'
                        self.hid_hider_command(command)
                        self.hiddenDevices.append(objItem.DeviceID)
                        self.add_log("Hiding device: " + str(objItem.DeviceID))

            with open(currentDirectory + "/res/devices.txt", "w") as file:
                for device in self.hiddenDevices:
                    file.write(device + "\n")

        if (controllerType == 'Xbox Controller'):
            # Unplug 
            messagebox.showinfo('Notice!', 'Please unplug your controller from the PC and press OK.')

        # Start emulation
        try:
            self.controller_reader[self.controllerInstance] = Controller()
            self.controller_reader[self.controllerInstance].emulate()
        except:
           print("Error: Failed to start controller emulation.")
           self.start_button.config(state="normal")
           return 
        
        if (controllerType == 'Xbox Controller'):
            # Wait for device to be replugged in
            messagebox.showinfo('Notice!', 'Please plug your controller back into the PC, wait a few seconds and then press OK.')
            
        self.controller_reader[self.controllerInstance].waitPeriod = False

        # Start the capture card
        try: 
            if (videoMode == "Capture Card"):
                self.capture_method = CaptureCard()
                capture_thread = threading.Thread(target=self.capture_method.start, daemon=True)
                capture_thread.start()
            elif(videoMode == "Desktop"):
                self.capture_method = CaptureDesktop()
                capture_thread = threading.Thread(target=self.capture_method.start, daemon=True)
                capture_thread.start()
        except:
            print("Error: Failed to start capture card.")
            self.start_button.config(state="normal")
            return 

        # Start the script
        try:
            moduleName = self.config.get_setting("script", "name", "None")

            if (moduleName != "None"):
                modulePath = os.path.dirname(os.path.abspath(__file__)) + f"\\scripts\\{moduleName}\\{moduleName}.py"

                if (not os.path.exists(modulePath)):
                    print("Loading compiled module...")
                    modulePath = os.path.dirname(os.path.abspath(__file__)) + f"\\scripts\\{moduleName}\\{moduleName}.cp38-win_amd64.pyd"

                spec = importlib.util.spec_from_file_location(moduleName, modulePath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                scriptClass = getattr(module, 'Script')
                self.moduleInstance = scriptClass(self.controller_reader[self.controllerInstance].emulated_controller, self.controller_reader[self.controllerInstance].actual_report)

                self.script_settings_window = None
                self.load_settings_window()

                self.script_running = True
                
                self.run_script()

            self.status_bar_left_label.config(text="Status: Running")
            self.start_button.config(text="Stop")
            self.start_button.config(state="normal")
            self.device_monitor_canvas.delete("all")
            self.device_monitor_template = ImageTk.PhotoImage(Image.open(currentDirectory + "/res/images/monitor.png"))
            self.device_monitor_canvas.image = self.device_monitor_template
            self.device_monitor_canvas.create_image(0, 0, image=self.device_monitor_canvas.image, anchor="nw")

            return True
        except Exception as e:
            print(e)
            self.stop(True)

    def kill_process_by_name(self, process_name):
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if proc.info['name'].lower() == process_name.lower():
                try:
                    psutil.Process(proc.info['pid']).terminate()
                    self.add_log("Closing process: " + str(proc.info['name']), "green")
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

    def stop(self, crashed = False):
        self.script_running = False

        if (crashed == False):
            self.run_script()

        self.add_log("Stopping script...", "red")

        self.status_bar_left_label.config(text="Status: Stopping...")
        self.start_button.config(text="Stoping...")
        self.start_button.config(state="disabled") 

        self.root.update_idletasks()

        if (len(self.hiddenDevices) > 0):
            for device in self.hiddenDevices:
                command = '"' + self.hidhide_cli_path + '" --dev-unhide "' + str(device) + '"'
                self.hid_hider_command(command)
                self.add_log("Unhiding device: " + str(device))
                self.root.update_idletasks()
        
        try:
            if (self.script_settings_window != None):
                self.script_settings_window.destroy()
        except:
            pass

        try:
            if (self.moduleInstance != None):
                self.moduleInstance.__del__()
                time.sleep(1)
                self.moduleInstance = None
        except:
            pass

        try:
            if (self.capture_method != None):
                self.capture_method.stop()
        except:
            pass

        try:
            if (self.controller_reader[self.controllerInstance] != None):
                self.controller_reader[self.controllerInstance].stop()
                self.controllerInstance += 1
        except:
            pass

        self.status_bar_left_label.config(text="Status: Stopped")
        self.start_button.config(text="Start")
        self.start_button.config(state="normal")    
                  

    def add_log(self, text, color="black", printNewLine=True):
        if (self.output_log == None):
            return
        
        self.output_log.config(state="normal")

        timeOfDay = time.strftime("%H:%M:%S", time.localtime())
        self.output_log.insert("end", "[" + timeOfDay + "] ", "black")

        newline = "\n"

        if (printNewLine == False):
            newline = ''

        self.output_log.insert("end", str(text) + newline, color)
        self.output_log.config(state="disabled")
        self.output_log.see("end")


    def center_window(self, window):
        window.update_idletasks()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        window_width = window.winfo_width()
        window_height = window.winfo_height()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        window.geometry(f"+{x}+{y}")

    def updateSetting(self, event):
        section, key = event.widget.config_target
        value = event.widget.get()
        self.config.set_setting(section, key, value)

    def update_slider_setting(self, entry, slider, field_info, event):
        type, section, key = event.widget.config_target

        if (type == 'onoff'):
            if (event.widget.get() == "Disabled"):
                value = False
            else:
                value = True
        else:
            value = event.widget.get()

        entry.delete(0, tk.END)
        entry.insert(0, str(value))

        self.script_settings.set_setting(section, key, value)
        
        if (self.moduleInstance != None):
            self.moduleInstance._set_settings(self.script_settings)

    def update_value_from_entry(self, entry, slider, field_info, section, event):
        try:
            val = float(entry.get())
        except:
            val = 0
        
        min = float(field_info['min'])
        max = float(field_info['max'])

        if (val < min):
            val = min

        if (val > max):
            val = max

        slider.set(val)
        self.script_settings.set_setting(section, 'value', val)

    def update_script_setting(self, event):
        type, section, key = event.widget.config_target

        if (type == 'onoff'):
            if (event.widget.get() == "Disabled"):
                value = False
            else:
                value = True
        else:
            value = event.widget.get()

        self.script_settings.set_setting(section, key, value)
        
        if (self.moduleInstance != None):
            self.moduleInstance._set_settings(self.script_settings)

    def show_input_device_settings(self):
            settings_window = tk.Toplevel(self.root)
            self.center_window(settings_window)
    
            settings_window.title("Input Device")
            settings_window.iconbitmap(currentDirectory + "/res/icons/joystick.ico")
            settings_window.resizable(0, 0)
            settings_window.attributes("-topmost", 1)

            device_index_label = ttk.Label(settings_window, text="Device Index")
            device_index_combo = ttk.Combobox(settings_window, values=["0", "1", "2", "3", "4", "5"], state="readonly")
            device_index_label.grid(row=0, column=0, padx=(10, 5), pady=(10, 5))
            device_index_combo.grid(row=1, column=0, padx=(10, 5), pady=(5, 10))
            device_index_combo.current(self.config.get_setting("input", "device_index", 0))
            device_index_combo.config_target = ['input', 'device_index']
            device_index_combo.bind("<<ComboboxSelected>>", self.updateSetting)

            read_mode_label = ttk.Label(settings_window, text="Device Type")
            read_mode_combo = ttk.Combobox(settings_window, values=["None", "Xbox Controller", "Playstation Controller"], state="readonly")
            read_mode_label.grid(row=0, column=1, padx=(5, 10), pady=(10, 5))
            read_mode_combo.grid(row=1, column=1, padx=(5, 10), pady=(5, 10))
            read_mode_combo.set(self.config.get_setting("input", "device_type", "None"))
            read_mode_combo.config_target = ['input', 'device_type']
            read_mode_combo.bind("<<ComboboxSelected>>", self.updateSetting)

            ok_button = ttk.Button(settings_window, text="Save", command=settings_window.destroy)
            ok_button.grid(row=2, column=0, columnspan=2, pady=(5, 10))

            settings_window.mainloop()

    def show_capture_settings(self):
            settings_window = tk.Toplevel(self.root)
            self.center_window(settings_window)
    
            settings_window.title("Capture Settings")
            settings_window.iconbitmap(currentDirectory + "/res/icons/zoom.ico")
            settings_window.resizable(0, 0)
            settings_window.attributes("-topmost", 1)

            def on_combobox_select(event):
                selected_value = device_index_combo.get()
                if selected_value == "Desktop":
                    read_mode_label.config(text="Monitor Index")
                    video_method_label.grid_forget()
                    video_method_combo.grid_forget()
                    video_resolution_label.grid_forget()
                    video_resolution_combo.grid_forget()
                    desktop_crop_mode_label.grid(row=4, column=0, padx=(10, 5), pady=(10, 5))
                    desktop_crop_mode_combo.grid(row=5, column=0, padx=(10, 5), pady=(5, 10))
                    left_crop_label.grid(row=6, column=0, padx=(10, 5), pady=(10, 5))
                    left_crop_entry.grid(row=7, column=0, padx=(10, 5), pady=(5, 10))
                    right_crop_label.grid(row=6, column=1, padx=(5, 10), pady=(10, 5))
                    right_crop_entry.grid(row=7, column=1, padx=(5, 10), pady=(5, 10))
                    top_crop_label.grid(row=8, column=0, padx=(10, 5), pady=(10, 5))
                    top_crop_entry.grid(row=9, column=0, padx=(10, 5), pady=(5, 10))
                    bottom_crop_label.grid(row=8, column=1, padx=(5, 10), pady=(10, 5))
                    bottom_crop_entry.grid(row=9, column=1, padx=(5, 10), pady=(5, 10))

                    on_cropmode_select(None)
                elif selected_value == "Capture Card":
                    read_mode_label.config(text="Video Index")
                    video_method_label.grid(row=2, column=0, padx=(10, 5), pady=(10, 5))
                    video_method_combo.grid(row=3, column=0, padx=(10, 5), pady=(5, 10))
                    video_resolution_label.grid(row=2, column=1, padx=(5, 10), pady=(10, 5))
                    video_resolution_combo.grid(row=3, column=1, padx=(5, 10), pady=(5, 10))
                    desktop_crop_mode_label.grid_forget()
                    desktop_crop_mode_combo.grid_forget()
                    left_crop_label.grid_forget()
                    left_crop_entry.grid_forget()
                    right_crop_label.grid_forget()
                    right_crop_entry.grid_forget()
                    top_crop_label.grid_forget()
                    top_crop_entry.grid_forget()
                    bottom_crop_label.grid_forget()
                    bottom_crop_entry.grid_forget()
                    width_center_crop_label.grid_forget()
                    width_center_crop_entry.grid_forget()
                    height_center_crop_label.grid_forget()
                    height_center_crop_entry.grid_forget()
                    left_crop_label.grid_forget()
                    left_crop_entry.grid_forget()
                    right_crop_label.grid_forget()
                    right_crop_entry.grid_forget()
                    top_crop_label.grid_forget()
                    top_crop_entry.grid_forget()
                    bottom_crop_label.grid_forget()
                    bottom_crop_entry.grid_forget()

                self.updateSetting(event)

            def on_cropmode_select(event):
                selected_value = desktop_crop_mode_combo.get()
                if selected_value == "Exact":
                    left_crop_label.grid(row=6, column=0, padx=(10, 5), pady=(10, 5))
                    left_crop_entry.grid(row=7, column=0, padx=(10, 5), pady=(5, 10))
                    right_crop_label.grid(row=6, column=1, padx=(5, 10), pady=(10, 5))
                    right_crop_entry.grid(row=7, column=1, padx=(5, 10), pady=(5, 10))
                    top_crop_label.grid(row=8, column=0, padx=(10, 5), pady=(10, 5))
                    top_crop_entry.grid(row=9, column=0, padx=(10, 5), pady=(5, 10))
                    bottom_crop_label.grid(row=8, column=1, padx=(5, 10), pady=(10, 5))
                    bottom_crop_entry.grid(row=9, column=1, padx=(5, 10), pady=(5, 10))
                    width_center_crop_label.grid_forget()
                    width_center_crop_entry.grid_forget()
                    height_center_crop_label.grid_forget()
                    height_center_crop_entry.grid_forget()
                elif selected_value == "From Center":
                    width_center_crop_label.grid(row=6, column=0, padx=(10, 5), pady=(10, 5))
                    width_center_crop_entry.grid(row=7, column=0, padx=(10, 5), pady=(5, 10))
                    height_center_crop_label.grid(row=6, column=1, padx=(5, 10), pady=(10, 5))
                    height_center_crop_entry.grid(row=7, column=1, padx=(5, 10), pady=(5, 10))
                    left_crop_label.grid_forget()
                    left_crop_entry.grid_forget()
                    right_crop_label.grid_forget()
                    right_crop_entry.grid_forget()
                    top_crop_label.grid_forget()
                    top_crop_entry.grid_forget()
                    bottom_crop_label.grid_forget()
                    bottom_crop_entry.grid_forget()

                if (event != None):
                    self.updateSetting(event)
            
            device_index_label = ttk.Label(settings_window, text="Capture Type")
            device_index_combo = ttk.Combobox(settings_window, values=["None", "Desktop", "Capture Card"], state="readonly")
            device_index_label.grid(row=0, column=0, padx=(10, 5), pady=(10, 5))
            device_index_combo.grid(row=1, column=0, padx=(10, 5), pady=(5, 10))
            device_index_combo.set(self.config.get_setting("capture", "type", "None"))
            device_index_combo.config_target = ['capture', 'type']
            device_index_combo.bind("<<ComboboxSelected>>", on_combobox_select)

            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop"):
                read_mode_label = ttk.Label(settings_window, text="Monitor Index")
                read_mode_label.grid(row=0, column=1, padx=(5, 10), pady=(10, 5))
            else:
                read_mode_label = ttk.Label(settings_window, text="Video Index")
                read_mode_label.grid(row=0, column=1, padx=(5, 10), pady=(10, 5))

            read_mode_combo = ttk.Combobox(settings_window, values=["0", "1", "2", "3", "4", "5"], state="readonly")
            read_mode_combo.grid(row=1, column=1, padx=(5, 10), pady=(5, 10))
            read_mode_combo.set(self.config.get_setting("capture", "index", 0))
            read_mode_combo.config_target = ['capture', 'index']
            read_mode_combo.bind("<<ComboboxSelected>>", self.updateSetting)

            fps_limit_label = ttk.Label(settings_window, text="FPS Limit")
            fps_limit_label.grid(row=0, column=2, padx=(5, 10), pady=(10, 5))
            fps_limit_combo = ttk.Combobox(settings_window, values=["15", "30", "60", "120", "144", "165", "240", "999"], state="readonly")
            fps_limit_combo.grid(row=1, column=2, padx=(5, 10), pady=(5, 10))
            fps_limit_combo.set(self.config.get_setting("capture", "fps_limit", 144))
            fps_limit_combo.config_target = ['capture', 'fps_limit']
            fps_limit_combo.bind("<<ComboboxSelected>>", self.updateSetting)

            video_method_label = ttk.Label(settings_window, text="Video Method")
            video_method_combo = ttk.Combobox(settings_window, values=["Microsoft Foundation", "Direct Show"], state="readonly")
            if (self.config.get_setting("capture", "type", "Desktop") == "Capture Card"):
                video_method_label.grid(row=2, column=0, padx=(10, 5), pady=(10, 5))
                video_method_combo.grid(row=3, column=0, padx=(10, 5), pady=(5, 10))
            video_method_combo.set(self.config.get_setting("capture", "video_capture_method", "Microsoft Foundation"))
            video_method_combo.config_target = ['capture', 'video_capture_method']
            video_method_combo.bind("<<ComboboxSelected>>", self.updateSetting)

            video_resolution_label = ttk.Label(settings_window, text="Video Resolution")
            video_resolution_combo = ttk.Combobox(settings_window, values=["3840x2160", "2560x1440", "1920x1080", "1280x720"], state="readonly")
            if (self.config.get_setting("capture", "type", "Desktop") == "Capture Card"):
                video_resolution_label.grid(row=2, column=1, padx=(5, 10), pady=(10, 5))
                video_resolution_combo.grid(row=3, column=1, padx=(5, 10), pady=(5, 10))
            video_resolution_combo.set(self.config.get_setting("capture", "video_capture_resolution", "1920x1080"))
            video_resolution_combo.config_target = ['capture', 'video_capture_resolution']
            video_resolution_combo.bind("<<ComboboxSelected>>", self.updateSetting)

            # create entry that accepts numbers only, for left, right, top and bottom crop
            def validate_crop_input(text):
                return text.isdigit() or text == ""
            
            vcmd = (settings_window.register(validate_crop_input), '%P')

            desktop_crop_mode_label = ttk.Label(settings_window, text="Crop Mode")
            desktop_crop_mode_combo = ttk.Combobox(settings_window, values=["Exact", "From Center"], state="readonly")
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop"):
                desktop_crop_mode_label.grid(row=4, column=0, padx=(10, 5), pady=(10, 5))
                desktop_crop_mode_combo.grid(row=5, column=0, padx=(10, 5), pady=(5, 10))
            desktop_crop_mode_combo.set(self.config.get_setting("capture", "crop_mode", "Exact"))
            desktop_crop_mode_combo.config_target = ['capture', 'crop_mode']
            desktop_crop_mode_combo.bind("<<ComboboxSelected>>", on_cropmode_select)

            left_crop_label = ttk.Label(settings_window, text="Left Crop")
            left_crop_entry = ttk.Entry(settings_window, validate="key", validatecommand=vcmd)
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop" and self.config.get_setting("capture", "crop_mode", "Exact") == "Exact"):
                left_crop_label.grid(row=6, column=0, padx=(10, 5), pady=(10, 5))
                left_crop_entry.grid(row=7, column=0, padx=(10, 5), pady=(5, 10))
            left_crop_entry.insert(0, self.config.get_setting("capture", "left_crop", 0))
            left_crop_entry.config_target = ['capture', 'left_crop']
            left_crop_entry.bind("<KeyRelease>", self.updateSetting)

            right_crop_label = ttk.Label(settings_window, text="Right Crop")
            right_crop_entry = ttk.Entry(settings_window, validate="key", validatecommand=vcmd)
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop" and self.config.get_setting("capture", "crop_mode", "Exact") == "Exact"):
                right_crop_label.grid(row=6, column=1, padx=(5, 10), pady=(10, 5))
                right_crop_entry.grid(row=7, column=1, padx=(5, 10), pady=(5, 10))
            right_crop_entry.insert(0, self.config.get_setting("capture", "right_crop", 0))
            right_crop_entry.config_target = ['capture', 'right_crop']
            right_crop_entry.bind("<KeyRelease>", self.updateSetting)

            top_crop_label = ttk.Label(settings_window, text="Top Crop")
            top_crop_entry = ttk.Entry(settings_window, validate="key", validatecommand=vcmd)
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop" and self.config.get_setting("capture", "crop_mode", "Exact") == "Exact"):
                top_crop_label.grid(row=8, column=0, padx=(10, 5), pady=(10, 5))
                top_crop_entry.grid(row=9, column=0, padx=(10, 5), pady=(5, 10))
            top_crop_entry.insert(0, self.config.get_setting("capture", "top_crop", 0))
            top_crop_entry.config_target = ['capture', 'top_crop']
            top_crop_entry.bind("<KeyRelease>", self.updateSetting)

            bottom_crop_label = ttk.Label(settings_window, text="Bottom Crop")
            bottom_crop_entry = ttk.Entry(settings_window, validate="key", validatecommand=vcmd)
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop" and self.config.get_setting("capture", "crop_mode", "Exact") == "Exact"):
                bottom_crop_label.grid(row=8, column=1, padx=(5, 10), pady=(10, 5))
                bottom_crop_entry.grid(row=9, column=1, padx=(5, 10), pady=(5, 10))
            bottom_crop_entry.insert(0, self.config.get_setting("capture", "bottom_crop", 0))
            bottom_crop_entry.config_target = ['capture', 'bottom_crop']
            bottom_crop_entry.bind("<KeyRelease>", self.updateSetting)

            width_center_crop_label = ttk.Label(settings_window, text="Width")
            width_center_crop_entry = ttk.Entry(settings_window, validate="key", validatecommand=vcmd)
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop" and self.config.get_setting("capture", "crop_mode", "Exact") == "From Center"):
                width_center_crop_label.grid(row=6, column=0, padx=(10, 5), pady=(10, 5))
                width_center_crop_entry.grid(row=7, column=0, padx=(10, 5), pady=(5, 10))
            width_center_crop_entry.insert(0, self.config.get_setting("capture", "center_crop_width", 0))
            width_center_crop_entry.config_target = ['capture', 'center_crop_width']
            width_center_crop_entry.bind("<KeyRelease>", self.updateSetting)

            height_center_crop_label = ttk.Label(settings_window, text="Height")
            height_center_crop_entry = ttk.Entry(settings_window, validate="key", validatecommand=vcmd)
            if (self.config.get_setting("capture", "type", "Desktop") == "Desktop" and self.config.get_setting("capture", "crop_mode", "Exact") == "From Center"):
                height_center_crop_label.grid(row=6, column=1, padx=(5, 10), pady=(10, 5))
                height_center_crop_entry.grid(row=7, column=1, padx=(5, 10), pady=(5, 10))
            height_center_crop_entry.insert(0, self.config.get_setting("capture", "center_crop_height", 0))
            height_center_crop_entry.config_target = ['capture', 'center_crop_height']
            height_center_crop_entry.bind("<KeyRelease>", self.updateSetting)

            ok_button = ttk.Button(settings_window, text="Save", command=settings_window.destroy)
            ok_button.grid(row=10, column=0, columnspan=4, pady=(10, 10))

            settings_window.mainloop()

    def show_mouse_calibration_settings(self):
            settings_window = tk.Toplevel(self.root)
            self.center_window(settings_window)
    
            settings_window.title("Mosue Calibration")
            settings_window.iconbitmap(currentDirectory + "/res/icons/computer-mouse.ico")
            settings_window.resizable(0, 0)
            settings_window.attributes("-topmost", 1)
            
            horizontal_sensitivity_slider = tk.Scale(settings_window, from_=0.01, to=20, resolution=0.05, length=400, orient='horizontal', label='Horizontal Sensitivity')
            horizontal_sensitivity_slider.grid(row=0, column=0, padx=10, pady=(10, 5), sticky='we')
            horizontal_sensitivity_slider.set(self.config.get_setting("mouse", "horizontal_sensitivity", 10))
            horizontal_sensitivity_slider.config_target = ['mouse', 'horizontal_sensitivity']
            horizontal_sensitivity_slider.bind("<ButtonRelease-1>", self.updateSetting)
            horizontal_sensitivity_slider.bind("<ButtonRelease-2>", self.updateSetting)
            horizontal_sensitivity_slider.bind("<ButtonRelease-3>", self.updateSetting)

            vertical_sensitivity_slider = tk.Scale(settings_window, from_=0.01, to=20, resolution=0.05, length=400, orient='horizontal', label='Vertical Sensitivity')
            vertical_sensitivity_slider.grid(row=1, column=0, padx=10, pady=(5, 5), sticky='we')
            vertical_sensitivity_slider.set(self.config.get_setting("mouse", "vertical_sensitivity", 10))
            vertical_sensitivity_slider.config_target = ['mouse', 'vertical_sensitivity']
            vertical_sensitivity_slider.bind("<ButtonRelease-1>", self.updateSetting)
            vertical_sensitivity_slider.bind("<ButtonRelease-2>", self.updateSetting)
            vertical_sensitivity_slider.bind("<ButtonRelease-3>", self.updateSetting)

            smoothness_slider = tk.Scale(settings_window, from_=1, to=20, resolution=1, length=400, orient='horizontal', label='Smoothness')
            smoothness_slider.grid(row=2, column=0, padx=10, pady=(5, 5), sticky='we')
            smoothness_slider.set(self.config.get_setting("mouse", "smoothness", 10))
            smoothness_slider.config_target = ['mouse', 'smoothness']
            smoothness_slider.bind("<ButtonRelease-1>", self.updateSetting)
            smoothness_slider.bind("<ButtonRelease-2>", self.updateSetting)
            smoothness_slider.bind("<ButtonRelease-3>", self.updateSetting)

            deadzone_slider = tk.Scale(settings_window, from_=0.01, to=1.00, resolution=0.01, length=400, orient='horizontal', label='Deadzone')
            deadzone_slider.grid(row=3, column=0, padx=10, pady=(5, 5), sticky='we')
            deadzone_slider.set(self.config.get_setting("mouse", "deadzone", 0.05))
            deadzone_slider.config_target = ['mouse', 'deadzone']
            deadzone_slider.bind("<ButtonRelease-1>", self.updateSetting)
            deadzone_slider.bind("<ButtonRelease-2>", self.updateSetting)
            deadzone_slider.bind("<ButtonRelease-3>", self.updateSetting)

            deadzone_amplification_slider = tk.Scale(settings_window, from_=1, to=2, resolution=0.01, length=400, orient='horizontal', label='Deadzone Amplification')
            deadzone_amplification_slider.grid(row=4, column=0, padx=10, pady=(5, 5), sticky='we')
            deadzone_amplification_slider.set(self.config.get_setting("mouse", "deadzone_amplification", 1.5))
            deadzone_amplification_slider.config_target = ['mouse', 'deadzone_amplification']
            deadzone_amplification_slider.bind("<ButtonRelease-1>", self.updateSetting)
            deadzone_amplification_slider.bind("<ButtonRelease-2>", self.updateSetting)
            deadzone_amplification_slider.bind("<ButtonRelease-3>", self.updateSetting)

            acceleration_dampener_slider = tk.Scale(settings_window, from_=0.01, to=1, resolution=0.01, length=400, orient='horizontal', label='Acceleration Dampener')
            acceleration_dampener_slider.grid(row=5, column=0, padx=10, pady=(5, 10), sticky='we')
            acceleration_dampener_slider.set(self.config.get_setting("mouse", "acceleration_dampener", 0.7))
            acceleration_dampener_slider.config_target = ['mouse', 'acceleration_dampener']
            acceleration_dampener_slider.bind("<ButtonRelease-1>", self.updateSetting)
            acceleration_dampener_slider.bind("<ButtonRelease-2>", self.updateSetting)
            acceleration_dampener_slider.bind("<ButtonRelease-3>", self.updateSetting)

            ok_button = ttk.Button(settings_window, text="Save", command=settings_window.destroy)
            ok_button.grid(row=6, column=0, columnspan=2, pady=(5, 10))

            settings_window.mainloop()

    def on_mouse_move(self, event):
        # print mouse position
        self.status_bar_left_label.config(text=f"Mouse Position: {event.x}, {event.y}")

    def updateSelf(self):
        messagebox.showinfo("Update", "CopyCat will now close to update. Re-launch CopyCat once the update is complete.")

        try:
            os.startfile('update.bat')
            self.close_app()
        except:
            print("Failed to update!")

    def refresh_scripts(self, event):
        scripts = ["None"]
        scripts.extend(get_directories('scripts'))

        self.script_combo["values"] = scripts

        currentScript = self.script_combo.get()
        
        if (currentScript in scripts):
            self.script_combo.set(currentScript)
        else:
            self.script_combo.set("None")

    def show_hid_hider(self):
        subprocess.Popen(self.hidhide_client_path)


    def compile_script_files(self):
        files = filedialog.askopenfilenames(title="Select Files to Encrypt", filetypes=[('Python Files', '*.py')])

        self.add_log("Compiling files...", "blue")

        if (len(files) > 0):
            for file in files:
                self.add_log("Compiling file: " + str(file), "blue")
                Encryptor(file)
                self.root.update_idletasks()

            self.add_log("Finished compiling files!", "green")

            messagebox.showinfo("Compile", "Finished compiling files!")


    def select_files_to_encrypt(self):
        files = filedialog.askopenfilenames(title="Select Files to Encrypt", filetypes=[('All Files', '*.*')])

        self.add_log("Encrypting files...", "blue")

        password = simpledialog.askstring("Password", "Enter a password to encrypt the files with", show="*")

        if (len(files) > 0):
            for file in files:
                self.add_log("Encrypting file: " + str(file), "blue")

                try:
                    pyAesCrypt.encryptFile(file, file + '.encrypted', password)
                except:
                    self.add_log("Failed to encrypt file: " + str(file), "red")

            self.add_log("Finished encrypting files!", "green")

            messagebox.showinfo("Encrypt", "Finished encrypting files!")

    def select_files_to_decrypt(self):
        files = filedialog.askopenfilenames(title="Select Files to Decrypt", filetypes=[('All Files', '*.*')])

        self.add_log("Decrypting files...", "blue")

        password = simpledialog.askstring("Password", "Enter a password to decrypt the files with", show="*")

        if (len(files) > 0):
            for file in files:
                self.add_log("Decrypting file: " + str(file), "blue")

                try:
                    pyAesCrypt.decryptFile(file, file.replace('.encrypted', '') + '.decrypted', password)
                except:
                    self.add_log("Failed to decrypt file: " + str(file), "red")

            self.add_log("Finished decrypting files!", "green")

            messagebox.showinfo("Decrypt", "Finished decrypting files!")

    def toggleAutoHide(self):
        if (self.config.get_setting('auto_hide', 'enabled', True)):
            self.home_menu.entryconfigure(0, label="❌    Auto Hide Devices")
            self.config.set_setting('auto_hide', 'enabled', False)
            self.add_log("Auto Hide Devices Disabled", "red")
        else:
            self.home_menu.entryconfigure(0, label="✔️Auto Hide Devices")
            self.config.set_setting('auto_hide', 'enabled', True)
            self.add_log("Auto Hide Devices Enabled", "green")

    def create_widgets(self):
        # add a menu bar
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # add a Home menu
        self.home_menu = tk.Menu(menu_bar, tearoff=0)

        if (self.config.get_setting('auto_hide', 'enabled', True)):
            self.home_menu.add_command(label="✔️Auto Hide Devices", command=self.toggleAutoHide)
        else:
            self.home_menu.add_command(label="❌    Auto Hide Devices", command=self.toggleAutoHide)

        self.home_menu.add_separator()
        self.home_menu.add_command(label="Exit", command=self.close_app)
        menu_bar.add_cascade(label="App", menu=self.home_menu)

        # add settings menu
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="Input Device", command=self.show_input_device_settings)
        #settings_menu.add_command(label="Mouse Calibration", command=self.show_mouse_calibration_settings)
        settings_menu.add_command(label="Capture Method", command=self.show_capture_settings)
        settings_menu.add_command(label="HidHider", command=self.show_hid_hider)
        menu_bar.add_cascade(label="Configuration", menu=settings_menu)

        tools_menu = tk.Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="Compile Script", command=self.compile_script_files)
        tools_menu.add_command(label="Encypt Weights/Files", command=self.select_files_to_encrypt)
        #tools_menu.add_command(label="Decrypt Weights/Files", command=self.select_files_to_decrypt)

        menu_bar.add_cascade(label="Tools", menu=tools_menu)

        # add a status bar that has 2 columns, the first column is 1/4 the width of the screen and the second column is 3/4 the width of the screen
        status_bar = tk.Frame(self.root)
        status_bar.grid(row=3, column=0, sticky="nsew")
        status_bar.config(borderwidth=0, relief="groove", padx=5, pady=5)
        status_bar.grid(padx=0, pady=(0, 0))

        # create a label for the left column of the status bar
        self.status_bar_left_label = tk.Label(status_bar, text="Waiting to run...")
        self.status_bar_left_label.pack(side="left", padx=(0, 5), pady=(0, 5))
        
        # create a label for the right column of the status bar
        status_bar_right_label = tk.Label(status_bar, text="Made with 💖 by StickAssist")
        status_bar_right_label.pack(side="right", padx=(5, 5), pady=(0, 5))

        # create a 3 column by 1 row grid layout, the bottom layout is full width
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=0)
        self.root.rowconfigure(2, weight=0)
        self.root.rowconfigure(3, weight=0)

        # create a frame for the middle column that is 50% width of screen
        topbar_frame = tk.Frame(self.root)
        topbar_frame.grid(row=0, column=0, sticky="nsew")
        topbar_frame.config(borderwidth=0, relief="groove", padx=0, pady=0)
        topbar_frame.grid(padx=(10, 10), pady=(10, 0))

        # create a frame for the right column that is 25% width of screen
        device_monitor_frame = tk.Frame(self.root)
        device_monitor_frame.grid(row=1, column=0, sticky="nsew")
        device_monitor_frame.config(borderwidth=2, relief="groove", padx=5, pady=5)
        device_monitor_frame.grid(padx=10, pady=(10, 5))

        # add a canavas that fills the device_monitor_frame, and add a image to it
        self.device_monitor_canvas = tk.Canvas(device_monitor_frame, width=640, height=360)
        self.device_monitor_canvas.pack(fill=tk.BOTH, expand=True)
        self.device_monitor_template = ImageTk.PhotoImage(Image.open("res/images/monitor.png"))
        self.device_monitor_canvas.image = self.device_monitor_template
        self.device_monitor_canvas.create_image(0, 0, image=self.device_monitor_canvas.image, anchor="nw")

        # when mouse moves over the canvas print out the position of the mouse on the canvas
        #self.device_monitor_canvas.bind("<Motion>", self.on_mouse_move)

        # add an inner frame to the middle frame, with two columns, the first column is 3/4 the width of the screen and the second column is 1/4 the width of the screen, containing a button and a label
        inner_frame = tk.Frame(topbar_frame)
        inner_frame.pack(fill=tk.BOTH, expand=False)

        # create a button for the inner frame
        self.start_button = ttk.Button(inner_frame, text="Start")
        self.start_button.pack(side="left", padx=(0, 5))
        self.start_button.bind("<Button-1>", self.start)

        # add a combo box to the inner frame
        scripts = ["None"]
        scripts.extend(get_directories('scripts'))
        currentScript = self.config.get_setting("script", "name", scripts[0])

        self.script_combo = ttk.Combobox(inner_frame, values=scripts, state="readonly")
        self.script_combo.pack(side="left", padx=0)
        self.script_combo.config_target = ['script', 'name']
        self.script_combo.bind("<<ComboboxSelected>>", self.updateSetting)

        if (currentScript in scripts):
            self.script_combo.set(currentScript)
        else:
            self.script_combo.set("None")

        #add refresh button that updates the script combo list
        refresh_button = ttk.Button(inner_frame, text="Refresh")
        refresh_button.pack(side="left", padx=(5, 0))
        refresh_button.bind("<Button-1>", self.refresh_scripts)

        # add a bottom frame that spans the entire width of the screen
        bottom_frame = tk.Frame(self.root)
        bottom_frame.grid(row=2, column=0, sticky="nsew")
        bottom_frame.config(borderwidth=0, relief="groove", padx=9, pady=0)
        bottom_frame.grid(padx=1, pady=(0, 10))

        # create a label for the bottom frame align text to the left
        bottom_label = tk.Label(bottom_frame, text="Output Log", anchor="w")
        bottom_label.pack(fill="both", expand=True, pady=(0, 5))

        # add a readonly text area to the bottom frame that spans the entire width of the screen
        self.output_log = tk.Text(bottom_frame, height=10, wrap="word", state="disabled")
        self.output_log.pack(fill="both", expand=True)
        fontSize = 9
        fontFamily = "Arial"
        self.output_log.tag_configure("bold-black", foreground="black", font=(fontFamily, fontSize, "bold"))
        self.output_log.tag_configure("bold-red", foreground="red", font=(fontFamily, fontSize, "bold"))
        self.output_log.tag_configure("bold-blue", foreground="blue", font=(fontFamily, fontSize, "bold"))
        self.output_log.tag_configure("bold-green", foreground="green", font=(fontFamily, fontSize, "bold"))
        self.output_log.tag_configure("black", foreground="black", font=(fontFamily, fontSize))
        self.output_log.tag_configure("red", foreground="red", font=(fontFamily, fontSize))
        self.output_log.tag_configure("blue", foreground="blue", font=(fontFamily, fontSize))
        self.output_log.tag_configure("green", foreground="green", font=(fontFamily, fontSize))

        self.add_log("Welcome to Copycat v" + str(self.version), "green")

    def run(self):
        self.root.mainloop()
