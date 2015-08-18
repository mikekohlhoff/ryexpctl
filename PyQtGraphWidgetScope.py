from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np

class PyQtGraphWidgetScope(QtGui.QGraphicsView):

    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=False)
        self.scopeWidget = pg.PlotWidget()
        self.scopeWidget.setTitle('Scope trace', size='12')

        self.vbl = QtGui.QVBoxLayout()
        self.vbl.addWidget(self.scopeWidget)
        self.setLayout(self.vbl)
        self.scopeWidget.setLabel('left', 'Signal', units='V')
        self.scopeWidget.setLabel('bottom', 'Time', units='s')
        self.scopeWidget.showGrid(x=False, y=True)
        self.scopeWidget.clear()

        self.lr1 = pg.LinearRegionItem([0,0], brush=pg.mkBrush(0,0,160,80))
        self.lr2 = pg.LinearRegionItem([0,0], brush=pg.mkBrush(52,124,23,80))
        self.lr1.setZValue(10)
        self.lr2.setZValue(10)
        self.scopeWidget.addItem(self.lr2)
        self.scopeWidget.addItem(self.lr1)
        self.lr1.setMovable(False)
        self.lr2.setMovable(False)
        
        # line for extraction pulse
        self.line1 = pg.InfiniteLine([0,0], pen=pg.mkPen('#990000', width=2, style=QtCore.Qt.DashLine))
        self.scopeWidget.addItem(self.line1)
        self.line1.setMovable(False)
        
    def plotMon(self, dataIn, timeincr):
        # reset mobility of cursors after data acquisition
        self.lr1.setMovable(True)
        self.lr2.setMovable(True)
        self.line1.setMovable(True)
        
        if np.size(self.scopeWidget.listDataItems()) > 0:
           self.scopeWidget.removeItem(self.scopeWidget.listDataItems()[0])
        # average traces, invert data, no integration over gate
        data = (sum(dataIn)/len(dataIn))*-1
        # substract baseline
        data = data - np.mean(data[0:100])
        plotTime = np.arange(np.size(data))*timeincr
        self.scopeWidget.plot(plotTime, data, pen=pg.mkPen('k', width=1.2))
        return data

    def plotDataAcq(self, dataIn, cursorPos, timeincr, linePos):
        # average traces
        data = (sum(dataIn)/len(dataIn))*-1
        data = data - np.mean(data[0:100])
        plotTime = np.arange(np.size(data))*timeincr
        self.scopeWidget.plot(plotTime, data, pen=pg.mkPen('k', width=1), clear=True)
        
        self.lr1 = pg.LinearRegionItem([cursorPos[0], cursorPos[1]], brush=pg.mkBrush(0,0,160,80))
        self.lr2 = pg.LinearRegionItem([cursorPos[2], cursorPos[3]], brush=pg.mkBrush(52,124,23,80))
        self.lr1.setMovable(False)
        self.lr2.setMovable(False)
        self.line1.setMovable(False)
        self.scopeWidget.addItem(self.lr1)
        self.scopeWidget.addItem(self.lr2)
        
        self.line1 = pg.InfiniteLine(linePos, pen=pg.mkPen('#990000', width=2, style=QtCore.Qt.DashLine))
        self.scopeWidget.addItem(self.line1)
        self.line1.setMovable(False)

    def getCursors(self):
        lr1Ret = self.lr1.getRegion()
        lr2Ret = self.lr2.getRegion() 
        return np.array([lr1Ret[0], lr1Ret[1], lr2Ret[0], lr2Ret[1]])
    
    def setCursors(self, cursorPos):
        self.lr1.setRegion([cursorPos[0], cursorPos[1]])
        self.lr2.setRegion([cursorPos[2], cursorPos[3]])

