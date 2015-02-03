from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np
import math
from pyqtgraph import mkPen

class PyQtGraphWidgetData(QtGui.QGraphicsView):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        pg.setConfigOption('background', None)
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=False)
        self.dataWidget = pg.PlotWidget()
        self.dataWidget.setTitle('Integrated gates', size='12')

        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.dataWidget)
        self.setLayout(self.vbl)
        self.dataWidget.setLabel('left', 'Integrated signal', units='arb')
        self.dataWidget.showGrid(x=False, y=True)
        self.plotTrace1 = []
        self.plotTrace2 = []

    def integrator(self, data, cPos):
        # integrate scope traces 
        intTrace = [sum(data[cPos[0]:cPos[1]]), sum(data[cPos[2]:cPos[3]])]
        return intTrace
    
    def plot(self, data, cursorPos, radioMode):
        plotData = self.integrator(data, cursorPos)
        self.plotTrace1.append(plotData[0])
        self.plotTrace2.append(plotData[1])
       # self.dataWidget.clear()
        self.dataWidget.plot(self.plotTrace1, pen=mkPen('#0000A0', width=1.2), clear=True)#, symbolBrush='#0000A0', symbolSize=4)
        self.dataWidget.plot(self.plotTrace2, pen=mkPen('#347C17', width=1.2), clear=False)#, symbolBrush='#347C17', symbolSize=4)
        if radioMode == 'volt':
            self.dataWidget.setLabel('bottom', 'Extraction Voltage', units='V')
        else:
            self.dataWidget.setLabel('bottom', '2nd Wavelength', units='nm')
