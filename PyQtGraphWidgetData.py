from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np
import math
from pyqtgraph import mkPen
from pyqtgraph import mkBrush

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
        self.dataWidget.setLabel('left', 'Integrated signal')
        self.dataWidget.showGrid(x=False, y=True)
        self.dataTrace1 = []
        self.dataTrace2 = []
        self.errTrace1 = []
        self.errTrace2 = []
        self.paramTrace = []
        
    def integrator(self, dataIn, cPos):
        # average scope traces and invert
        data = (sum(dataIn)/len(dataIn))*-1
        # substract baseline
        data = data - np.mean(data[0:100])
        # std deviation for average
        dataIn = np.vstack(dataIn)
        err = np.std(dataIn, axis=0)
        # TOF windows
        intTrace = [sum(data[cPos[0]:cPos[1]]), sum(data[cPos[2]:cPos[3]])]       
        # error propagation
        err = [np.sqrt(sum(np.square(err[cPos[0]:cPos[1]]))), np.sqrt(sum(np.square(err[cPos[2]:cPos[3]])))]
        return intTrace, err
    
    def plot(self, dataIn, setParam, cPosIn, scanParam, ti):
        cPos = [round(cPosIn[0]/ti), round(cPosIn[1]/ti), round(cPosIn[2]/ti), round(cPosIn[3]/ti)]
        data, err = self.integrator(dataIn, cPos)
       
        self.paramTrace.append(float(setParam))
        self.dataTrace1.append(float(data[0]))
        self.dataTrace2.append(float(data[1]))
        self.errTrace1.append(float(err[0]))
        self.errTrace2.append(float(err[1]))
               
        # convert error to display version, error as band with data as line inbetween
        X = self.paramTrace
        errPlot1 = [np.asarray(self.dataTrace1)+0.5*np.asarray(self.errTrace1), np.asarray(self.dataTrace1)-0.5*np.asarray(self.errTrace1)]
        errPlot2 = [np.asarray(self.dataTrace2)+0.5*np.asarray(self.errTrace2), np.asarray(self.dataTrace2)-0.5*np.asarray(self.errTrace2)]
        e11 = self.dataWidget.plot(X, errPlot1[0], pen=mkPen('#0000A0', width=0.5), clear=True)
        e12 = self.dataWidget.plot(X, errPlot1[1], pen=mkPen('#0000A0', width=0.5))
        e21 = self.dataWidget.plot(X, errPlot2[0], pen=mkPen('#347C17', width=0.5))
        e22 = self.dataWidget.plot(X, errPlot2[1], pen=mkPen('#347C17', width=0.5))
        fillErr1 = pg.FillBetweenItem(e11, e12, brush=mkBrush(0,0,160,80))
        fillErr2 = pg.FillBetweenItem(e21, e22, brush=mkBrush(52,124,23,80))
        self.dataWidget.addItem(fillErr1)
        self.dataWidget.addItem(fillErr2)
        # actual averaged data
        self.dataWidget.plot(X, self.dataTrace1, pen=mkPen('#0000A0', width=1.5, style=QtCore.Qt.DashLine))
        self.dataWidget.plot(X, self.dataTrace2, pen=mkPen('#347C17', width=1.5, style=QtCore.Qt.DashLine))
        # overlay with scatter to discern parameter spacing
        self.dataWidget.plot(X, self.dataTrace1, symbolBrush='#0000A0', symbolSize=4)
        self.dataWidget.plot(X, self.dataTrace2, symbolBrush='#347C17', symbolSize=4)
        
        if 'Voltage' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='V')
        elif 'Wavelength' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='nm')
        elif 'Delay' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='s')
   