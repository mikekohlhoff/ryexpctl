from PyQt4 import QtGui
import pyqtgraph as pg
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.widgets import Cursor
from pylab import *
import numpy as np
import math

class PyQtGraphWidgetScope(QtGui.QWidget):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        pg.setConfigOption('background', None)
        pg.setConfigOption('foreground', 'k')
        self.scopeWidget = pg.PlotWidget()
        #self.scopeWidget = pg.plot(title="Scope trace")

        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.scopeWidget)
        self.setLayout(self.vbl)
        
    def plot(self, data):
        self.scopeWidget.clear()
        self.scopeWidget.plot(data, pen='b')
        #self.canvas.ax.set_title('Scope trace signal', fontsize=12)
        #self.canvas.ax.set_xlabel(r'Time ($\mu$s)', fontsize=12)
        #self.canvas.ax.set_ylabel('Amplitude (V)', fontsize=12)
        #self.canvas.ax.axis([-0.02*len(data), len(data)*1.02, min(data)*1.2, max(data)*1.2])
        #self.canvas.ax.grid(True)


