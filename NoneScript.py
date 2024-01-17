from ScriptCore import Template

class Script(Template):

    def __init__(self, controller, report):
        super().__init__(controller, report)
        
    def run(self, frame):
        return frame

