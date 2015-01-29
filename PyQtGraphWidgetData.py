from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np
import math

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
        self.dataWidget.showGrid(x=True, y=True)

        self.intgrTrace = []

    def integrator(self, data):
        # integrate scope traces 
        intTrace = sum(data) 
        return intTrace
    
    def plot(self,data, radioMode):
        plotData = self.integrator(data)
        self.intgrTrace = np.append(self.intgrTrace, plotData)
        self.dataWidget.clear()

        self.dataWidget.plot(self.intgrTrace, pen='b', symbolBrush='b', symbolSize=4)
        if radioMode == 'volt':
            self.dataWidget.setLabel('bottom', 'Extraction Voltage', units='V')
        else:
            self.dataWidget.setLabel('bottom', '2nd Wavelength', units='nm')
