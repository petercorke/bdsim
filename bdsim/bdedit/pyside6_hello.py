import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel
from PySide6.QtGui import QIcon
#from PySide6.QtCore import pyqtSlot

def window():
   app = QApplication(sys.argv)
   widget = QWidget()

   textLabel = QLabel(widget)
   textLabel.setText("Hello World!")
   textLabel.move(110,85)

   widget.setGeometry(50,50,320,200)
   widget.setWindowTitle("PySide6 Example")
   widget.show()
   sys.exit(app.exec_())

if __name__ == '__main__':
   window()
