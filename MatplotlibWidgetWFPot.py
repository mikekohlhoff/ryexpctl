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


class MatplotlibWidgetWFPot(QtGui.QWidget):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
        self.canvas.ax.set_title('Calculated PCB electrode potentials', fontsize=10)
        self.canvas.fig.patch.set_alpha(0)
        params = {
                  'legend.fontsize': 8,
                  'xtick.labelsize': 8,
                  'ytick.labelsize': 8,
                  'legend.handletextpad': .5,
                }
        plt.rcParams.update(params)

        
    def plot(self, wfPotentials):
        if hasattr(wfPotentials, 'plotTime'):
            argX = wfPotentials.plotTime
            argY = wfPotentials.potentialsOut
            self.canvas.ax.clear()
            self.canvas.ax.plot(argX, argY[0,:], 'b', label="1", linewidth=1.5)
            self.canvas.ax.plot(argX, argY[1,:], 'r', label="2", linewidth=1.5)
            self.canvas.ax.plot(argX, argY[2,:], 'g', label="3", linewidth=1.5)
            self.canvas.ax.plot(argX, argY[3,:], 'b--', label="4", linewidth=1.5)
            self.canvas.ax.plot(argX, argY[4,:], 'r--', label="5", linewidth=1.5)
            self.canvas.ax.plot(argX, argY[5,:], 'g--', label="6", linewidth=1.5)
            self.canvas.ax.axis([-2, wfPotentials.plotTime[-1]+0.5, wfPotentials.maxAmp*-2-10, wfPotentials.maxAmp*2+10])
            self.canvas.ax.grid(True)
            self.canvas.ax.set_title("Calculated PCB electrode potentials", fontsize=10)
            self.canvas.ax.set_xlabel("Time ($\mu$s)", fontsize=10)
            self.canvas.ax.set_ylabel("Amplitude (bits)", fontsize=10)
            self.canvas.ax.legend(loc="lower right",  bbox_to_anchor = [.7,0.06], fontsize=8)
            # mares in potential generation 
            self.canvas.ax.plot([wfPotentials.incplTime,wfPotentials.incplTime],[(wfPotentials.maxAmp*2+10),\
            (wfPotentials.maxAmp*(-2)-10)], 'k--', linewidth=1.5)
            self.canvas.ax.plot([wfPotentials.plotTime[-1]-wfPotentials.outcplTime, wfPotentials.plotTime[-1]-wfPotentials.outcplTime], \
            [wfPotentials.maxAmp*-2-1,wfPotentials.maxAmp*2+1], 'k--', linewidth=1.5)
            #self.WaveformDisplay.canvas.ax.plot([wfPotentials.incplTime+wfPotentials.decelTime,\
            #wfPotentials.incplTime+wfPotentials.decelTime],[wfPotentials.maxAmp*-2-1, wfPotentials.maxAmp*2+1], 'k--', linewidth=1)
            self.canvas.fig.patch.set_alpha(0)
            self.canvas.fig.tight_layout()
            self.canvas.draw()
        else:
            print 'No potentials generated'
