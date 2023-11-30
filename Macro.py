import time
import random

MACRO_STATE_STOPPED = 0
MACRO_STATE_RUNNING = 1

class Macro():
    current_action = 0
    state = MACRO_STATE_STOPPED
    actions = []
    start_time = time.time()
    pause_time = time.time()
    isWaiting = False
    controller = None

    def __init__(self, controller, actions):
        self.actions = actions
        self.controller = controller

    def stop(self):
        self.current_action = len(self.actions) - 1

    def run(self):
        if (self.state != MACRO_STATE_RUNNING):
            self.state = MACRO_STATE_RUNNING
            self.isWaiting = False
            self.current_action = 0
            self.pause_time = time.time()
            self.start_time = time.time()

    def isRunning(self):
        return self.state == MACRO_STATE_RUNNING
    
    def isStopped(self):
        return self.state == MACRO_STATE_STOPPED

    def cycle(self):
        if (self.state == MACRO_STATE_STOPPED):
            return
        
        action = self.actions[self.current_action]

        if (action[0] == "wait"):
            if (self.isWaiting == False):
                self.pause_time = time.time()
                self.isWaiting = True

                return
            else:
                time_elapsed = (time.time() - self.pause_time) * 1000

                if (time_elapsed >= action[1]):
                    self.isWaiting = False
                else:
                    return
                
        elif (action[0] == "wait_random"):
            if (self.isWaiting == False):
                self.pause_time = time.time()
                self.isWaiting = True

                return
            else:
                time_elapsed = (time.time() - self.pause_time) * 1000

                if (time_elapsed >= random.randint(action[1], action[2])):
                    self.isWaiting = False
                else:
                    return
                
        else:
            try:
                if (action[0] in ["wait"]):
                    action[0](*[action[1]])

                elif (action[0].__name__ in ["press_button", "release_button", "press_dpad_button", "release_dpad_button", "right_trigger_float", "left_trigger_float"]):
                    action[0](*[action[1]])

                elif (action[0].__name__ in ["left_joystick_float", "right_joystick_float"]):
                    action[0](*action[1])
            except Exception as e:
                print(e)
                print("Error running macro action: ", action[0].__name__)
                
        self.current_action += 1

        if (self.current_action >= len(self.actions)):
            self.current_action = 0
            self.state = MACRO_STATE_STOPPED

        return
