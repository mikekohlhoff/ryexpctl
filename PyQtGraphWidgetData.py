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
        self.dataWidget.setLabel('left', 'Integrated TOF signal')
        self.dataWidget.showGrid(x=False, y=True)
        self.dataTrace1 = []
        self.dataTrace2 = []
        self.paramTrace = []
        self.dataTracePrev1 = []
        self.dataTracePrev2 = []

    def integrator(self, data1, data2, cPos):
        # integration over TOF windows
        intTrace = [sum(data1[cPos[0]:cPos[1]]), sum(data2[cPos[2]:cPos[3]])]

        return intTrace

    def plot(self, dataIn1, dataIn2, setParam, cPosIn, scanParam, ti1, ti2, to1, to2):
        # gate1: trace1, gate2: trace2
        # offset correction of indices
        vertoff1 = round(to1/ti1)
        vertoff2 = round(to2/ti2)

        cPos = [round(cPosIn[0]/ti1) - vertoff1, round(cPosIn[1]/ti1) - vertoff1, \
                round(cPosIn[2]/ti2) - vertoff2, round(cPosIn[3]/ti2) - vertoff2]

        data = self.integrator(dataIn1, dataIn2, cPos)

        # append data lists point wise
        self.paramTrace.append(float(setParam))
        self.dataTrace1.append(float(data[0]))
        self.dataTrace2.append(float(data[1]))

        X = self.paramTrace
        # averaged data
        self.dataWidget.plot(X, self.dataTrace1, pen=mkPen('#0000A0'), clear=True)
        self.dataWidget.plot(X, self.dataTrace2, pen=mkPen('#347C17'))

        if 'Voltage' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='V')
        elif 'Wavelength' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='nm')
        elif 'Delay' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='s')

    def plotMatrix(self, dataIn1, dataIn2, setParam, cPosIn, scanParam, ti1, ti2, tracelen, countpoints, numpoints, mode):
        cPos = [round(cPosIn[0]/ti1), round(cPosIn[1]/ti1), round(cPosIn[2]/ti2), round(cPosIn[3]/ti2)]
        data = self.integrator(dataIn1, dataIn2, cPos)

        # write data to buffer file
        if countpoints == 1:
            self.f_buffer = open('tempdata.txt', 'w')
        if mode == 'Velocity':
            line = str.format('{:d}', setParam[0]) + '\t' + str.format('{:.11f}', setParam[1]) + '\t' + str.format('{:.3f}', data[0]) + \
            '\t' + str.format('{:.3f}', data[1]) + '\n'
        elif mode == 'Detection':
            line = str.format('{:d}', setParam[0]) + '\t' + str.format('{:d}', setParam[1]) + '\t' + str.format('{:.3f}', data[0]) + \
            '\t' + str.format('{:.3f}', data[1]) + '\n'
        self.f_buffer.write(line)
        if countpoints == numpoints:
            self.f_buffer.close()

        self.dataWidget.clear()
        if len(self.dataTracePrev1) > 0:
                self.dataWidget.plot(self.paramTracePrev, self.dataTracePrev1, pen=mkPen('#2a2a2a'))
                self.dataWidget.plot(self.paramTracePrev, self.dataTracePrev2, pen=mkPen('#2a2a2a'))

        # store data for single trace current and last one before
        self.paramTrace.append([setParam[0],setParam[1]])
        self.dataTrace1.append(data[0])
        self.dataTrace2.append(data[1])

        # convert data for plotting
        param = np.asarray(self.paramTrace)[:,0]
        dat1 = np.asarray(self.dataTrace1)
        dat2 = np.asarray(self.dataTrace2)

        # averaged data
        self.dataWidget.plot(param, dat1, pen=mkPen('#0000A0'))
        self.dataWidget.plot(param, dat2, pen=mkPen('#347C17'))

        self.dataWidget.setLabel('bottom', 'Extraction Voltage', units='V')
        if len(self.paramTrace) == tracelen and not(countpoints == numpoints):
            self.paramTracePrev = np.asarray(self.paramTrace)[:,0]
            self.dataTracePrev1 = self.dataTrace1
            self.dataTracePrev2 = self.dataTrace2

            self.dataTrace1 = []
            self.dataTrace2 = []
            self.paramTrace = []
