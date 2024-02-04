import os
import Gui

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class Application:
    gui = None

    def __init__(self):
        self.gui = Gui.Gui()

    def run(self):
        self.gui.run()

if __name__ == "__main__":
    app = Application()
    app.run()
    +