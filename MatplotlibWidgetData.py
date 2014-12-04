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
        
    def plot(self):
        self.WaveformDisplay.canvas.ax.clear()
           # self.WaveformDisplay.canvas.ax.plot(argX, argY[0,:], 'b', label="1", linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.plot(argX, argY[1,:], 'r', label="2", linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.plot(argX, argY[2,:], 'g', label="3", linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.plot(argX, argY[3,:], 'b--', label="4", linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.plot(argX, argY[4,:], 'r--', label="5", linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.plot(argX, argY[5,:], 'g--', label="6", linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.axis([-2, self.wfPotentials.plotTime[-1]+0.5, self.wfPotentials.maxAmp*-2-10, self.wfPotentials.maxAmp*2+10])
           # self.WaveformDisplay.canvas.ax.grid(True)
           # self.WaveformDisplay.canvas.ax.set_title("Calculated PCB potentials")
           # self.WaveformDisplay.canvas.ax.set_xlabel("Time ($\mu$s)")
           # self.WaveformDisplay.canvas.ax.set_ylabel("Amplitude (bits)")
           # self.WaveformDisplay.canvas.ax.legend(loc="lower right")
           # # mark different phases in potential generation 
           # self.WaveformDisplay.canvas.ax.plot([self.wfPotentials.incplTime,self.wfPotentials.incplTime],[(self.wfPotentials.maxAmp*2+10),\
           # (self.wfPotentials.maxAmp*(-2)-10)], 'k--', linewidth=1.5)
           # self.WaveformDisplay.canvas.ax.plot([self.wfPotentials.plotTime[-1]-self.wfPotentials.outcplTime,\
           # self.wfPotentials.plotTime[-1]-self.wfPotentials.outcplTime], [self.wfPotentials.maxAmp*-2-1,self.wfPotentials.maxAmp*2+1], 'k--', \
           # linewidth=1.5)
           # #self.WaveformDisplay.canvas.ax.plot([self.wfPotentials.incplTime+self.wfPotentials.decelTime,\
           # #self.wfPotentials.incplTime+self.wfPotentials.decelTime],[self.wfPotentials.maxAmp*-2-1, self.wfPotentials.maxAmp*2+1], 'k--', linewidth=1)
           # self.WaveformDisplay.canvas.fig.patch.set_alpha(0)
           # self.WaveformDisplay.canvas.fig.tight_layout()
           # self.WaveformDisplay.canvas.draw()

