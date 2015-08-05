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


class MatplotlibWidgetData(QtGui.QWidget):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
        self.canvas.ax.set_title('Integrated traces', fontsize=12)
        self.canvas.fig.patch.set_alpha(0)
        self.intgrTrace = []
        
    def integrator(self, data):
        # integrate scope traces
        intTrace = sum(data) 
        return intTrace
    
    def plot(self,data, radioMode):
        plotData = self.integrator(data)
        self.intgrTrace = np.append(self.intgrTrace, plotData)
        self.canvas.ax.clear()
        self.canvas.ax.plot(self.intgrTrace, 'b.-')
        self.canvas.ax.set_title('Integrated traces', fontsize=12)
        if radioMode == 'volt':
            self.canvas.ax.set_xlabel('Extraction Voltage (V)', fontsize=12)
        else:
            self.canvas.ax.set_xlabel(r'2nd Wavelength ($\lambda$)', fontsize=12)
        self.canvas.ax.set_ylabel('Amplitude (arb.u.)', fontsize=12)
        if len(self.intgrTrace) > 1:
            self.canvas.ax.axis([-0.02*len(self.intgrTrace), len(self.intgrTrace)*1.02, \
            min(self.intgrTrace)*1.2, max(self.intgrTrace)*1.2])
        self.canvas.fig.patch.set_alpha(0)
        self.canvas.fig.tight_layout()
        self.canvas.draw()
