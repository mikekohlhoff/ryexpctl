from PyQt4 import QtGui
import sys

class ExpandBox(QtGui.QWidget)
    def __init__(self, parent=None)
        QtGui.QWidget.__init__(self, parent)
        





#class ExpanderWidget(QtGui.QWidget):
#    def __init__(self, text, widget, parent=None):
#        super(ExpanderWidget, self).__init__(parent)
#
#        self.layout = QtGui.QVBoxLayout()
#
#        # better use your own icons
#        # these are kind of ugly :)
#        style = QtGui.QCommonStyle()
#        self.rightArrow = style.standardIcon(QtGui.QStyle.SP_ArrowRight)
#        self.downArrow = style.standardIcon(QtGui.QStyle.SP_ArrowDown)
#
#        self.toggle = QtGui.QPushButton(self.downArrow, text)
#        self.toggle.clicked.connect(self.toggleWidget)
#
#        self.widget = widget
#
#        self.layout.addWidget(self.toggle)
#        self.layout.addWidget(self.widget)
#        self.setLayout(self.layout)
#
#    def toggleWidget(self):
#        if self.widget.isVisible():
#            self.toggle.setIcon(self.rightArrow)
#            self.widget.setVisible(False)
#        else:
#            self.toggle.setIcon(self.downArrow)
#            self.widget.setVisible(True)
#
#"""A Expander widget similar to the GtkExpander."""
#
#from PyQt4.QtCore import pyqtSignal
#from PyQt4.QtGui import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
#from PyQt4.QtGui import QPainter, QStyle, QStyleOption, QWidget
#
##from ubuntu_sso.qt.arrow import QArrow
#
## we are following the Qt style, lets tell pylint to ignore it
## pylint: disable=C0103
#
#class QExpanderLabel(QWidget):
#    """Widget used to show the label of a QExpander."""
#
#    clicked = pyqtSignal()
#
#    def __init__(self, label, parent=None):
#        """Create a new instance."""
#        super(QExpanderLabel, self).__init__(parent)
#        self.arrow = QArrow(QArrow.RIGHT)
#        self.label = QLabel(label)
#        layout = QHBoxLayout()
#        layout.setContentsMargins(0, 0, 0, 0)
#        self.setLayout(layout)
#        layout.addWidget(self.arrow)
#        layout.addWidget(self.label)
#
#    def mousePressEvent(self, event):
#        """Mouse clicked."""
#        if self.arrow.direction == QArrow.DOWN:
#            self.arrow.direction = QArrow.RIGHT
#        else:
#            self.arrow.direction = QArrow.DOWN
#        self.clicked.emit()
#
#    def text(self):
#        """Return the text of the label."""
#        return self.label.text()
#
#    def setText(self, text):
#        """Set the text of the label."""
#        self.label.setText(text)
#
#
#class QExpander(QWidget):
#    """A Qt implementation similar to GtkExpander."""
#
#    def __init__(self, label, expanded=False, parent=None):
#        """Create a new instance."""
#        super(QExpander, self).__init__(parent)
#        self.label = QExpanderLabel(label)
#        self.label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
#        self.content = None
#        self.layout = QVBoxLayout()
#        self.layout.setContentsMargins(0, 0, 0, 0)
#        self.setLayout(self.layout)
#        self.layout.addWidget(self.label)
#        self.layout.addStretch()
#        self.label.clicked.connect(self._on_label_clicked)
#        self.setExpanded(expanded)
#
#    def _on_label_clicked(self):
#        """The expander widget was clicked."""
#        self._expanded = not self._expanded
#        self.setExpanded(self._expanded)
#
#    def addWidget(self, widget):
#        """Add a widget to the expander.
#
#        The previous widget will be removed.
#        """
#        if self.content is not None:
#            self.layout.removeWidget(self.content)
#        self.content = widget
#        self.content.setVisible(self._expanded)
#        self.layout.insertWidget(1, self.content)
#
#    def text(self):
#        """Return the text of the label."""
#        return self.label.text()
#
#    def setText(self, text):
#        """Set the text of the label."""
#        self.label.setText(text)
#
#    def expanded(self):
#        """Return if widget is expanded."""
#        return self._expanded
#
#    # pylint: disable=W0201
#    def setExpanded(self, is_expanded):
#        """Expand the widget or not."""
#        self._expanded = is_expanded
#        if self._expanded:
#            self.label.arrow.direction = QArrow.DOWN
#        else:
#            self.label.arrow.direction = QArrow.RIGHT
#        if self.content is not None:
#            self.content.setVisible(self._expanded)
#    # pylint: enable=W0201
# 
#class QArrow(QWidget):
#    """Qt implementation similar to GtkArrow."""
# 
#    UP = 0
#    DOWN = 1
#    LEFT = 2
#    RIGHT = 3
# 
#    def __init__(self, direction, parent=None):
#        """Create a new instance."""
#        QWidget.__init__(self, parent)
#        if not direction in (QArrow.UP, QArrow.DOWN, QArrow.LEFT, QArrow.RIGHT):
#            raise ValueError('Wrong arrow direction.')
#        self._direction = direction
#
#    def paintEvent(self, event):
#        """Paint a nice primitive arrow."""
#        opt = QStyleOption()
#        opt.initFrom(self)
#        p = QPainter(self)
#        if self._direction == QArrow.UP:
#            primitive = QStyle.PE_IndicatorArrowUp
#        elif self._direction == QArrow.DOWN:
#            primitive = QStyle.PE_IndicatorArrowDown
#        elif self._direction == QArrow.LEFT:
#            primitive = QStyle.PE_IndicatorArrowLeft
#        else:
#            primitive = QStyle.PE_IndicatorArrowRight
#        self.style().drawPrimitive(primitive, opt, p, self)
