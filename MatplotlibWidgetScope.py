from PyQt4 import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from pylab import *
import numpy as np
import math

class MplCanvas(FigureCanvas):

    def __init__(self):
        self.fig = Figure()
        self.ax = self.fig.add_subplot(111)

        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MatplotlibWidgetScope(QtGui.QWidget):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
        self.canvas.ax.set_title('Scope trace signal')
        self.canvas.ax.set_xlabel(r'Time ($\mu$s)')
        self.canvas.ax.set_ylabel('Amplitude (V)')
        self.canvas.fig.patch.set_alpha(0)
        self.canvas.fig.tight_layout()
        #font = FontProperties().copy()
        
    def plot(self, data):
        self.canvas.ax.clear()
        self.canvas.ax.plot(data)
        self.canvas.ax.set_title('Scope trace signal')
        self.canvas.ax.set_xlabel(r'Time ($\mu$s)')
        self.canvas.ax.set_ylabel('Amplitude (V)')
        self.canvas.ax.axis([-0.02*len(data), len(data)*1.02, min(data)*1.2, max(data)*1.2])
        self.canvas.ax.grid(True)
        self.canvas.fig.patch.set_alpha(0)
        self.canvas.fig.tight_layout()
        self.canvas.draw()
