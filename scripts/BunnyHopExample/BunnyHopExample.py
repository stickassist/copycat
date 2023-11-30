from ScriptCore import Template, PrintColors
from ControllerMapping import Buttons
from Macro import Macro

# This is an example script that will be run by the main program.
class Script(Template):
    def __init__(self, controller, report):
        super().__init__(controller, report)

        # Setup a macro
        self.bunny_hop = Macro(controller, [
            [self.release_button, Buttons.BTN_SOUTH],
            ["wait", 50],
            [self.press_button, Buttons.BTN_SOUTH],
            ["wait", 50],
            [self.release_button, Buttons.BTN_SOUTH]
        ])
        
    def run(self, frame):
        # Start Bunny hop macro when the X/A button is pressed
        if (self.is_actual_button_pressed(Buttons.BTN_SOUTH)):
            self.print_log("Bunny Hop Macro running", PrintColors.COLOR_GREEN)
            self.bunny_hop.run()

        # Cycle the macro, this iterate through he macro actions loop at a time
        self.bunny_hop.cycle()

        return frame

