import vgamepad as vg
import os, time, threading, inputs, numpy as np
from ctypes import Structure, c_ushort, c_uint8, c_float

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

from Config import Config

from ControllerMapping import mappingXbox, mappingDS4

STATE_STOPPED = 0
STATE_RUNNING = 1

TYPE_XINPUT = "Xbox Controller"
TYPE_DINPUT = "Playstation Controller"
TYPE_MKB = "Mouse & Keyboard"

currentDirectory = os.path.dirname(os.path.abspath(__file__))

class ControllerReport(Structure):
    _fields_ = [("type", c_uint8),
                ("buttons", c_ushort),
                ("special", c_ushort),
                ("leftTrigger", c_float),
                ("rightTrigger", c_float),
                ("thumbLX", c_float),
                ("thumbLY", c_float),
                ("thumbRX", c_float),
                ("thumbRY", c_float)]
    
class Controller:
    config = None
    state = STATE_STOPPED
    emulated_controller = None

    controller_type = TYPE_XINPUT
    controller_index = 0
    thread = None
    waitPeriod = True

    actual_report = ControllerReport(
        type=0,
        buttons=0,
        special=0,
        leftTrigger=0,
        rightTrigger=0,
        thumbLX=0,
        thumbLY=0,
        thumbRX=0,
        thumbRY=0
    )

    def __init__(self):
        self.config = Config(currentDirectory + '/res/config.ini')
        self.controller_index = self.config.get_setting("input", "device_index", 0)
        self.controller_type = self.config.get_setting("input", "device_type", TYPE_XINPUT)
        

    def emulate(self):
        self.state = STATE_RUNNING

        if (self.controller_type == TYPE_XINPUT):
            print("Emulating XInput controller.")
            self.actual_report.type = 0
            self.emulated_controller = vg.VX360Gamepad()
            self.thread = threading.Thread(target=self.captureXInput, daemon=True)
            self.thread.start()

        elif (self.controller_type == TYPE_DINPUT):
            print("Emulating DInput controller.")
            self.actual_report.type = 1
            self.emulated_controller = vg.VDS4Gamepad()
            self.thread = threading.Thread(target=self.captureDirectInput, daemon=True)
            self.thread.start()

        elif (self.controller_type == TYPE_MKB):
            print("Not yet implemented!")


    def stop(self):
        self.state = STATE_STOPPED
        self.waitPeriod = False
        self.thread = None
        print("Stopping controller emulation...")
        time.sleep(1)

        self.emulated_controller.__del__()


    def mapRange(self, value, from_min, from_max, to_min, to_max):
        value = max(from_min, min(from_max, value))
        ratio = (value - from_min) / (from_max - from_min)
        mapped_value = to_min + ratio * (to_max - to_min)
        return mapped_value


    def captureXInput(self):
        joystick = None

        # Wait for controller to be connected
        print("Waiting for controller to be connected...")

        while(self.waitPeriod):
            time.sleep(0.1)

        while(joystick == None and self.state == STATE_RUNNING):
            try:
                joystick = inputs.devices.gamepads[self.controller_index]
            except Exception as e:
                print("Error initialising controller on index:" + str(self.controller_index))
                print("Error: " + str(e))
                joystick = None

            time.sleep(0.1)

        print("Controller connected.")

        # Map controller buttons to XInput buttons
        while self.state == STATE_RUNNING:
            try:
                events = joystick.read()
            except:
                print("Error reading controller events.")
                break
            
            try:
                self.actual_report.type = 0

                for event in events:
                    if (event.ev_type == "Absolute"):
                        if (event.code in ['ABS_HAT0X', 'ABS_HAT0Y']):
                            if (event.state != 0):
                                self.emulated_controller.press_button(mappingXbox['hats'][event.code][event.state])
                                self.actual_report.buttons |= mappingXbox['hats'][event.code][event.state]
                            else:
                                self.emulated_controller.release_button(mappingXbox['hats'][event.code][-1])
                                self.emulated_controller.release_button(mappingXbox['hats'][event.code][1])
                                self.actual_report.buttons &= ~mappingXbox['hats'][event.code][-1]
                                self.actual_report.buttons &= ~mappingXbox['hats'][event.code][1]
                        
                        if (event.code == 'ABS_Z'):
                            self.emulated_controller.left_trigger(event.state)
                            self.actual_report.leftTrigger = event.state

                        if (event.code == 'ABS_RZ'):
                            self.emulated_controller.right_trigger(event.state)
                            self.actual_report.rightTrigger = event.state

                        if (event.code == 'ABS_X'):
                            axisValue = self.mapRange(event.state, -32768, 32767, -1, 1)
                            self.emulated_controller.report.sThumbLX = event.state
                            self.actual_report.thumbLX = axisValue

                        if (event.code == 'ABS_Y'):
                            axisValue = self.mapRange(event.state, -32768, 32767, -1, 1)
                            self.emulated_controller.report.sThumbLY = event.state
                            self.actual_report.thumbLY = axisValue

                        if (event.code == 'ABS_RX'):
                            axisValue = self.mapRange(event.state, -32768, 32767, -1, 1)
                            self.emulated_controller.report.sThumbRX = event.state
                            self.actual_report.thumbRX = axisValue

                        if (event.code == 'ABS_RY'):
                            axisValue = self.mapRange(event.state, -32768, 32767, -1, 1)
                            self.emulated_controller.report.sThumbRY = event.state
                            self.actual_report.thumbRY = -axisValue

                    if (event.ev_type == "Key"):
                        if (event.state == 1):
                            self.emulated_controller.press_button(mappingXbox['buttons'][event.code])
                            self.actual_report.buttons |= mappingXbox['buttons'][event.code]
                        else:
                            self.emulated_controller.release_button(mappingXbox['buttons'][event.code])
                            self.actual_report.buttons &= ~mappingXbox['buttons'][event.code]
            except Exception as e:
                print("ERROR OCCURED CAPTURING:", e)

        print("Controller disconnected.")


    def captureDirectInput(self):
        pygame.init()
        pygame.joystick.init()

        joystick = None

        # Wait for controller to be connected
        print("Waiting for controller to be connected...")

        while(joystick == None and self.state == STATE_RUNNING):
            try:
                joystick = pygame.joystick.Joystick(self.controller_index)
                joystick.init()
            except Exception as e:
                print("Error initialising controller on index:" + str(self.controller_index))
                print("Error: " + str(e))
                joystick = None

            time.sleep(0.1)

        if (joystick == None):
            print("Controller not found.")
            self.state = STATE_STOPPED
            return

        print("Controller connected.")

        dPadSates = {
            11: False,
            12: False,
            13: False,
            14: False,
        }

        while self.state == STATE_RUNNING:
            try:
                events = pygame.event.get()
            except:
                print("1# Error reading controller events.")
                self.state = STATE_STOPPED
                break
            
            try:
                self.actual_report.type = 1

                if (self.emulated_controller == None):
                    print("2# Error reading controller events.")
                    self.state = STATE_STOPPED
                    continue

                for event in events:
                    if event.type == pygame.JOYAXISMOTION:
                        if (event.axis == 4):
                            triggerValue = self.mapRange(event.value, -1, 1, 0, 1)
                            self.emulated_controller.left_trigger_float(triggerValue)
                            self.actual_report.leftTrigger = triggerValue

                            if (triggerValue > 0):
                                self.emulated_controller.press_button(vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)
                                self.actual_report.buttons |= vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT
                            else:
                                self.emulated_controller.release_button(vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT)
                                self.actual_report.buttons &= ~vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT

                        if (event.axis == 5):
                            triggerValue = self.mapRange(event.value, -1, 1, 0, 1)
                            self.emulated_controller.right_trigger_float(triggerValue)
                            self.actual_report.rightTrigger = triggerValue

                            if (triggerValue > 0):
                                self.emulated_controller.press_button(vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)
                                self.actual_report.buttons |= vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT
                            else:
                                self.emulated_controller.release_button(vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT)
                                self.actual_report.buttons &= ~vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT

                        if (event.axis == 0):
                            self.emulated_controller.report.bThumbLX = 128 + round(event.value * 127)
                            self.actual_report.thumbLX = np.clip(event.value, -1, 1)

                        if (event.axis == 1):
                            self.emulated_controller.report.bThumbLY = 128 + round(event.value * 127)
                            self.actual_report.thumbLY = np.clip(event.value, -1, 1)

                        if (event.axis == 2):
                            self.emulated_controller.report.bThumbRX = 128 + round(event.value * 127)
                            self.actual_report.thumbRX = np.clip(event.value, -1, 1)

                        if (event.axis == 3):
                            self.emulated_controller.report.bThumbRY = 128 + round(event.value * 127)
                            self.actual_report.thumbRY = np.clip(event.value, -1, 1)

                    elif event.type == pygame.JOYBUTTONDOWN:
                        if (event.button in [15, 5, 16]):
                            self.emulated_controller.press_special_button(mappingDS4['buttons'][event.button])
                            self.actual_report.special |= mappingDS4['buttons'][event.button]
                        elif (event.button in [11, 12, 13, 14]):
                            dPadSates[event.button] = True

                            if (dPadSates[11] and dPadSates[13]):
                                self.emulated_controller.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST)
                                self.actual_report.buttons &= ~0xF
                                self.actual_report.buttons |= vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
                            elif (dPadSates[11] and dPadSates[14]):
                                self.emulated_controller.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST)
                                self.actual_report.buttons &= ~0xF
                                self.actual_report.buttons |= vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
                            elif (dPadSates[12] and dPadSates[13]):
                                self.emulated_controller.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST)
                                self.actual_report.buttons &= ~0xF
                                self.actual_report.buttons |= vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
                            elif (dPadSates[12] and dPadSates[14]):
                                self.emulated_controller.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST)
                                self.actual_report.buttons &= ~0xF
                                self.actual_report.buttons |= vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
                            else:
                                self.emulated_controller.directional_pad(mappingDS4['buttons'][event.button])
                                self.actual_report.buttons &= ~0xF
                                self.actual_report.buttons |= mappingDS4['buttons'][event.button]
                        else:
                            self.emulated_controller.press_button(mappingDS4['buttons'][event.button])
                            self.actual_report.buttons |= mappingDS4['buttons'][event.button]

                    elif event.type == pygame.JOYBUTTONUP:
                        if (event.button in [15, 5, 16]):
                            self.emulated_controller.release_special_button(mappingDS4['buttons'][event.button])
                            self.actual_report.special &= ~mappingDS4['buttons'][event.button]
                        elif (event.button in [11, 12, 13, 14]):
                            dPadSates[event.button] = False
                            self.emulated_controller.directional_pad(vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)
                            self.actual_report.buttons &= ~vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHWEST
                            self.actual_report.buttons &= ~vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTHEAST
                            self.actual_report.buttons &= ~vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHWEST
                            self.actual_report.buttons &= ~vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTHEAST
                            self.actual_report.buttons &= ~0xF
                            self.actual_report.buttons |= vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE
                        else:
                            self.emulated_controller.release_button(mappingDS4['buttons'][event.button])
                            self.actual_report.buttons &= ~mappingDS4['buttons'][event.button]

                self.emulated_controller.update()
                
            except Exception as e:
                print("ERROR OCCURED CAPTURING:", e)
    
        if (joystick != None):
            print ("Ending controller capture...")
            joystick.quit()
        
        pygame.quit()
        print("Controller disconnected.")
        