import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from Application import *

if __name__ == "__main__":
    app = Application()
    app.run()