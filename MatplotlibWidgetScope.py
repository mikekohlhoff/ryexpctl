from PyQt4 import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.widgets import Cursor
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
        self.canvas.ax.set_title('Scope trace signal', fontsize=12)
        self.canvas.fig.patch.set_alpha(0)
        
    def plot(self, data, cursorPos):
        cursorPos = cursorPos.astype(np.float)
        self.canvas.ax.clear()
        self.canvas.ax.plot(data)
        self.drawCursors(cursorPos)
        self.canvas.ax.set_title('Scope trace signal', fontsize=12)
        self.canvas.ax.set_xlabel(r'Time ($\mu$s)', fontsize=12)
        self.canvas.ax.set_ylabel('Amplitude (V)', fontsize=12)
        self.canvas.ax.axis([-0.02*len(data), len(data)*1.02, min(data)*1.2, max(data)*1.2])
        self.canvas.ax.grid(True)
        self.canvas.fig.patch.set_alpha(0)
        self.canvas.fig.tight_layout()
        cursor = Cursor(self.canvas.ax, useblit=True, color='red', linewidth=2 )
        self.canvas.draw()

    def redraw(self, cursorPos):
        if hasattr(self, 'cursorId'):
            # delete old cursor position
            for i in range(0,4):
                self.canvas.ax.lines.remove(self.cursorId[i])
        self.drawCursors(cursorPos)
        self.canvas.draw()
        
    def drawCursors(self,cursorPos):
        x, xx, y, yy = self.canvas.ax.axis()
        ca = self.canvas.ax.plot([cursorPos[0], cursorPos[0]], [y, yy], 'k-', linewidth=1.5)
        cb = self.canvas.ax.plot([cursorPos[1], cursorPos[1]], [y, yy], 'k--', linewidth=1.5)
        cc = self.canvas.ax.plot([cursorPos[2], cursorPos[2]], [y, yy], '-', color=[.5,.5,.5], linewidth=1.5)
        cd = self.canvas.ax.plot([cursorPos[3], cursorPos[3]], [y, yy], '--', color=[.5,.5,.5], linewidth=1.5)
        self.cursorId = np.array([ca, cb, cc, cd])
