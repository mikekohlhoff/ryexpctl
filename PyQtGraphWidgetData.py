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
        self.errTrace1 = []
        self.errTrace2 = []
        self.paramTrace = []
        self.dataTracePrev1 = []
        self.dataTracePrev2 = []

    def integrator(self, dataIn1, dataIn2, cPos):
        # average scope traces and invert
        data1 = (sum(dataIn1)/len(dataIn1))*-1
        data2 = (sum(dataIn2)/len(dataIn2))*-1
        # substract baseline
        #data1 = data1 - np.mean(data1[-2000:-1000])
        #data2 = data2 - np.mean(data2[-2000:-1000])
        # std deviation for average
        dataerr1 = np.vstack(dataIn1)
        dataerr2 = np.vstack(dataIn2)
        err1 = np.std(dataerr1, axis=0)
        err2 = np.std(dataerr2, axis=0)
        # TOF windows
        intTrace = [sum(data1[cPos[0]:cPos[1]]), sum(data2[cPos[2]:cPos[3]])]
        # error propagation
        err = [np.sqrt(sum(np.square(err1[cPos[0]:cPos[1]]))), np.sqrt(sum(np.square(err2[cPos[2]:cPos[3]])))]
        return intTrace, err

    def plot(self, dataIn1, dataIn2, setParam, cPosIn, scanParam, ti1, ti2):
        # gate1: trace1, gate2: trace2
        cPos = [round(cPosIn[0]/ti1), round(cPosIn[1]/ti1), round(cPosIn[2]/ti2), round(cPosIn[3]/ti2)]
        data, err = self.integrator(dataIn1, dataIn2, cPos)

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
        if 'Voltage' in scanParam:
            self.dataWidget.plot(X, self.dataTrace1, symbolBrush='#0000A0', symbolSize=4)
            self.dataWidget.plot(X, self.dataTrace2, symbolBrush='#347C17', symbolSize=4)

        if 'Voltage' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='V')
        elif 'Wavelength' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='nm')
        elif 'Delay' in scanParam:
            self.dataWidget.setLabel('bottom', scanParam, units='s')

    def plotMatrix(self, dataIn1, dataIn2, setParam, cPosIn, scanParam, ti1, ti2, tracelen, countpoints, numpoints, mode):
        cPos = [round(cPosIn[0]/ti1), round(cPosIn[1]/ti1), round(cPosIn[2]/ti2), round(cPosIn[3]/ti2)]
        data, err = self.integrator(dataIn1, dataIn2, cPos)

        # write data to buffer file
        if countpoints == 1:
            self.f_buffer = open('tempdata.txt', 'w')
        if mode == 'Velocity':
            line = str.format('{:d}', setParam[0]) + '\t' + str.format('{:.11f}', setParam[1]) + '\t' + str.format('{:.3f}', data[0]) + '\t' + \
                              str.format('{:.3f}', err[0]) + '\t' + str.format('{:.3f}', data[1]) + '\t' + str.format('{:.3f}', err[1]) + '\n'
        elif mode == 'Detection':
            line = str.format('{:d}', setParam[0]) + '\t' + str.format('{:d}', setParam[1]) + '\t' + str.format('{:.3f}', data[0]) + '\t' + \
                              str.format('{:.3f}', err[0]) + '\t' + str.format('{:.3f}', data[1]) + '\t' + str.format('{:.3f}', err[1]) + '\n'
        self.f_buffer.write(line)
        if countpoints == numpoints:
            self.f_buffer.close()

        self.dataWidget.clear()
        if len(self.dataTracePrev1) > 0:
                self.dataWidget.plot(self.paramTracePrev, self.dataTracePrev1, pen=mkPen('#2a2a2a', width=0.5))
                self.dataWidget.plot(self.paramTracePrev, self.dataTracePrev2, pen=mkPen('#2a2a2a', width=0.5))

        # store data for single trace current and last one before
        self.paramTrace.append([setParam[0],setParam[1]])
        self.dataTrace1.append(data[0])
        self.dataTrace2.append(data[1])
        self.errTrace1.append(err[0])
        self.errTrace2.append(err[1])

        # convert data for plotting
        param = np.asarray(self.paramTrace)[:,0]
        dat1 = np.asarray(self.dataTrace1)
        dat2 = np.asarray(self.dataTrace2)
        err1 = np.asarray(self.errTrace1)
        err2 = np.asarray(self.errTrace2)

        errPlot1 = [dat1+0.5*err1, dat1-0.5*err1]
        errPlot2 = [dat2+0.5*err2, dat2-0.5*err2]

        e11 = self.dataWidget.plot(param, errPlot1[0], pen=mkPen('#0000A0', width=0.5))
        e12 = self.dataWidget.plot(param, errPlot1[1], pen=mkPen('#0000A0', width=0.5))
        e21 = self.dataWidget.plot(param, errPlot2[0], pen=mkPen('#347C17', width=0.5))
        e22 = self.dataWidget.plot(param, errPlot2[1], pen=mkPen('#347C17', width=0.5))
        fillErr1 = pg.FillBetweenItem(e11, e12, brush=mkBrush(0,0,160,80))
        fillErr2 = pg.FillBetweenItem(e21, e22, brush=mkBrush(52,124,23,80))
        self.dataWidget.addItem(fillErr1)
        self.dataWidget.addItem(fillErr2)
        # actual averaged data
        self.dataWidget.plot(param, dat1, pen=mkPen('#0000A0', width=0.5, style=QtCore.Qt.DashLine))
        self.dataWidget.plot(param, dat2, pen=mkPen('#347C17', width=0.5, style=QtCore.Qt.DashLine))

        self.dataWidget.setLabel('bottom', 'Extraction Voltage', units='V')
        if len(self.paramTrace) == tracelen and not(countpoints == numpoints):
            self.paramTracePrev = np.asarray(self.paramTrace)[:,0]
            self.dataTracePrev1 = self.dataTrace1
            self.dataTracePrev2 = self.dataTrace2

            self.dataTrace1 = []
            self.dataTrace2 = []
            self.errTrace1 = []
            self.errTrace2 = []
            self.paramTrace = []
