from PyQt4 import QtGui
from matplotlib.backends.backend_qt4agg import (
FigureCanvasQTAgg as FigureCanvas,
 NavigationToolbar2QT as NavigationToolbar)

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


class MatplotlibWidgetWFPot(QtGui.QGraphicsView):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
        self.canvas.ax.set_title('Calculated PCB electrode potentials', fontsize=10)
        self.canvas.fig.patch.set_alpha(0)
        self.mpl_toolbar = NavigationToolbar(self.canvas, self)
        params = {
                  'legend.fontsize': 8,
                  'xtick.labelsize': 8,
                  'ytick.labelsize': 8,
                  'legend.handletextpad': .5,
                }
        plt.rcParams.update(params)
        self.mpl_toolbar.pan()

        
    def plot(self, wfPotentials, plotitems):
        if hasattr(wfPotentials, 'plotTime'):
            argX = wfPotentials.plotTime
            argY = wfPotentials.potentialsOut
            # get axis limits to not reset zoom/pan
            axlim = self.canvas.ax.axis()
            self.canvas.ax.clear()
            if not any(plotitems):
                self.canvas.draw()
                return
            if plotitems[0]:
                self.canvas.ax.plot(argX, argY[1,:], 'r.')
                self.canvas.ax.plot(argX, argY[1,:], 'r', label="2", linewidth=1.2)
            if plotitems[1]:
                self.canvas.ax.plot(argX, argY[3,:], 'b.')
                self.canvas.ax.plot(argX, argY[3,:], 'b', label="4", linewidth=1.2)
            if plotitems[2]:
                self.canvas.ax.plot(argX, argY[5,:], 'g.')
                self.canvas.ax.plot(argX, argY[5,:], 'g', label="6", linewidth=1.2)
            if not axlim == (0.0, 1.0, 0.0, 1.0):
                self.canvas.ax.axis(axlim)
            else: pass
            self.canvas.ax.grid(True)
            self.canvas.ax.set_title("Calculated PCB electrode potentials", fontsize=10)
            self.canvas.ax.set_xlabel("Time ($\mu$s)", fontsize=10)
            self.canvas.ax.set_ylabel("Amplitude (bits)", fontsize=10)
            self.canvas.ax.legend(bbox_to_anchor=(0.02, 0.99), loc=2, borderpad=None, borderaxespad=0., fontsize=8, frameon=False)
            # mares in potential generation 
            self.canvas.ax.plot([wfPotentials.incplTime,wfPotentials.incplTime],[(wfPotentials.maxAmp*2+50),-50], 'k--', linewidth=1.5)
            self.canvas.ax.plot([wfPotentials.plotTime[-1]-wfPotentials.outcplTime, wfPotentials.plotTime[-1]-wfPotentials.outcplTime], \
            [-1,wfPotentials.maxAmp*2+1], 'k--', linewidth=1.5)
            #self.WaveformDisplay.canvas.ax.plot([wfPotentials.incplTime+wfPotentials.decelTime,\
            #wfPotentials.incplTime+wfPotentials.decelTime],[wfPotentials.maxAmp*-2-1, wfPotentials.maxAmp*2+1], 'k--', linewidth=1)
            self.canvas.fig.patch.set_alpha(0)
            self.canvas.fig.tight_layout()
            self.canvas.draw()
        else:
            print 'No potentials generated'
