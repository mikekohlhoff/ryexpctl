from PyQt4 import QtGui
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from pylab import *

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
        #self.canvas.ax.set_title('Calculated PCB Potentials')
        #self.canvas.ax.set_xlabel(r'Time ($\mu$s)')
        #self.canvas.ax.set_ylabel('Amplitude (bits)')
        self.canvas.fig.patch.set_alpha(0)
        self.canvas.fig.tight_layout()
        #font = FontProperties().copy()
        


