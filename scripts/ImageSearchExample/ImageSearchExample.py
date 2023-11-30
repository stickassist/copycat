import cv2
from ControllerMapping import Buttons
from Macro import Macro
from ScriptCore import Template, PrintColors

class Script(Template):
    def __init__(self, controller, report):
        super().__init__(controller, report)

        self.leaf = cv2.imread('scripts/TestScript/leaf.png')
        
    def run(self, frame):

        result = self.search_image(frame, self.leaf, 0.95)

        if (result != None):
            cv2.rectangle(frame, result[0], result[1], (0,0,255), 5)

        return frame