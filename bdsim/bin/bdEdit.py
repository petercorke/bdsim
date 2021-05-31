import sys

from PyQt5.QtWidgets import *

from bdedit.interface import Interface

if __name__ == '__main__':
    app = QApplication(sys.argv)

    screen_resolution = app.desktop().screenGeometry()
    window = Interface(screen_resolution)

    sys.exit(app.exec_())