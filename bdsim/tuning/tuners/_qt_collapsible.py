# adapted from https://github.com/By0ute/pyqt-collapsible-widget
__author__ = 'Caroline Beyne'

from PyQt5 import QtWidgets, QtCore, QtGui


class Collapsible(QtWidgets.QWidget):
    def __init__(self, title=None, parent=None, collapsed=True):
        super().__init__(parent)

        self.is_collapsed = collapsed
        self._title_frame = None
        self._content, self._content_layout = (None, None)

        self._main_v_layout = QtWidgets.QVBoxLayout(self)
        self._main_v_layout.setContentsMargins(0, 0, 0, 0)
        self._main_v_layout.addWidget(
            self.initTitleFrame(title))
        self._main_v_layout.addWidget(self.initContent(self.is_collapsed))

    def initTitleFrame(self, title):
        self._title_frame = self.TitleFrame(title=title,
                                            collapsed=self.is_collapsed,
                                            on_clicked=self.toggleCollapsed,
                                            parent=self)

        return self._title_frame

    def initContent(self, collapsed):
        self._content = QtWidgets.QWidget(self)
        self._content_layout = QtWidgets.QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        self._content.setLayout(self._content_layout)
        self._content.setVisible(not collapsed)

        return self._content

    def addWidget(self, widget):
        self._content_layout.addWidget(widget)

    def clear(self):
        self._content_layout.clear()

    def toggleCollapsed(self):
        self._content.setVisible(self.is_collapsed)
        self.is_collapsed = not self.is_collapsed
        self._title_frame._arrow.setArrow(int(self.is_collapsed))

    ############################
    #           TITLE          #
    ############################
    class TitleFrame(QtWidgets.QFrame):
        def __init__(self, on_clicked, parent=None, title="", collapsed=False):
            super().__init__(parent=parent)

            self.setMinimumHeight(24)
            self.move(QtCore.QPoint(24, 0))
            self.setStyleSheet("border:1px solid rgb(41, 41, 41); ")

            self._hlayout = QtWidgets.QHBoxLayout(self)
            self._hlayout.setContentsMargins(0, 0, 0, 0)
            self._hlayout.setSpacing(0)

            self._arrow = None
            self._title = None

            self._hlayout.addWidget(self.initArrow(collapsed))
            self._hlayout.addWidget(self.initTitle(title))
            self.on_clicked = on_clicked

        def initArrow(self, collapsed):
            self._arrow = Collapsible.Arrow(collapsed, self)
            self._arrow.setStyleSheet("border:0px")

            return self._arrow

        def initTitle(self, title=None):
            self._title = QtWidgets.QLabel(title, self)
            self._title.setMinimumHeight(24)
            self._title.move(QtCore.QPoint(24, 0))
            self._title.setStyleSheet("border:0px")

            return self._title

        def mousePressEvent(self, event):
            self.on_clicked()

            return super().mousePressEvent(event)

    #############################
    #           ARROW           #
    #############################
    class Arrow(QtWidgets.QFrame):
        def __init__(self, collapsed=False, parent=None):
            super().__init__(parent=parent)

            self.setMaximumSize(24, 24)

            # horizontal == 0
            self._arrow_horizontal = (QtCore.QPointF(7.0, 8.0),
                                      QtCore.QPointF(17.0, 8.0),
                                      QtCore.QPointF(12.0, 13.0))
            # vertical == 1
            self._arrow_vertical = (QtCore.QPointF(8.0, 7.0),
                                    QtCore.QPointF(13.0, 12.0),
                                    QtCore.QPointF(8.0, 17.0))
            # arrow
            self._arrow = None
            self.setArrow(int(collapsed))

        def setArrow(self, arrow_dir):
            if arrow_dir:
                self._arrow = self._arrow_vertical
            else:
                self._arrow = self._arrow_horizontal

        def paintEvent(self, event):
            painter = QtGui.QPainter()
            painter.begin(self)
            painter.setBrush(QtGui.QColor(192, 192, 192))
            painter.setPen(QtGui.QColor(64, 64, 64))
            painter.drawPolygon(*self._arrow)
            painter.end()
