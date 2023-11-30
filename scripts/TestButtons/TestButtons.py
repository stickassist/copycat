import cv2
from ControllerMapping import Buttons
from Macro import Macro
from ScriptCore import Template, PrintColors
import numpy as np

class Script(Template):
    def __init__(self, controller, report):
        super().__init__(controller, report)

    def run(self, frame):

        moveX = self.get_actual_left_stick_x()
        moveY= self.get_actual_left_stick_y()
        aimX = self.get_actual_right_stick_x()
        aimY = self.get_actual_right_stick_y()

        if (self.is_actual_special_button_pressed(Buttons.BTN_GUIDE)):
            self.print_log("Guide/PS pressed")

        if (self.is_actual_special_button_pressed(Buttons.BTN_TOUCHPAD)):
            self.print_log("Touchpad pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_SOUTH)):
            self.say("Cross pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_EAST)):
            self.print_log("Cricle pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_NORTH)):
            self.print_log("Triangle pressed")
        
        if (self.is_actual_button_pressed(Buttons.BTN_WEST)):
            self.print_log("Square pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_LEFT_SHOULDER)):
            self.print_log("Left one pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_RIGHT_SHOULDER)):
            self.print_log("Right one pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_BACK)):
            self.print_log("Back pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_OPTIONS)):
            self.print_log("Options pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_LEFT_THUMB)):
            self.print_log("Left Thumbstick pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_RIGHT_THUMB)):
            self.print_log("Right Thumbstick pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_DPAD_UP)):
            self.print_log("D-Pad Up pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_DPAD_DOWN)):
            self.print_log("D-Pad Down pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_DPAD_LEFT)):
            self.print_log("D-Pad Left pressed")

        if (self.is_actual_button_pressed(Buttons.BTN_DPAD_RIGHT)):
            self.print_log("D-Pad Right pressed")

        if (self.get_actual_left_trigger() > 0):
            self.print_log("Left Trigger pressed: " + str(self.get_actual_left_trigger()), PrintColors.COLOR_BLUE)

        if (self.get_actual_right_trigger() > 0):
            self.print_log("Right Trigger pressed:" + str(self.get_actual_right_trigger()), PrintColors.COLOR_BLUE)

        if (abs(self.get_actual_left_stick_x()) >= 0.10):
            self.print_log("Left Stick X: " + str(self.get_actual_left_stick_x()), PrintColors.COLOR_BLUE)

        if (abs(self.get_actual_left_stick_y()) >= 0.10):
            self.print_log("Left Stick Y: " + str(self.get_actual_left_stick_y()), PrintColors.COLOR_BLUE)

        if (abs(self.get_actual_right_stick_x()) >= 0.10):
            self.print_log("Right Stick X: " + str(self.get_actual_right_stick_x()), PrintColors.COLOR_BLUE)

        if (abs(self.get_actual_right_stick_y()) >= 0.10):
            self.print_log("Right Stick Y: " + str(self.get_actual_right_stick_y()), PrintColors.COLOR_BLUE)

        self.left_joystick_float(np.clip(moveX, -1, 1), np.clip(moveY, -1, 1))
        self.right_joystick_float(np.clip(aimX, -1, 1), np.clip(aimY, -1, 1))

        return frame

