from PyQt4 import QtGui
import pyqtgraph as pg
import numpy as np
import math

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
        self.scopeWidget.showGrid(x=True, y=True)
        self.scopeWidget.clear()

        self.lr1 = pg.LinearRegionItem([0,0])
        self.lr2 = pg.LinearRegionItem([0,0])
        self.lr1.setZValue(10)
        self.lr2.setZValue(10)
        self.scopeWidget.addItem(self.lr1)
        self.scopeWidget.addItem(self.lr2)

    def plotMon(self, data):
        if np.size(self.scopeWidget.listDataItems()) > 0:
            self.scopeWidget.removeItem(self.scopeWidget.listDataItems()[0])
        self.scopeWidget.plot(data, pen='b')

        lr1Ret = self.lr1.getRegion()
        lr2Ret = self.lr2.getRegion()
        return np.array([lr1Ret[0], lr1Ret[1], lr2Ret[0], lr2Ret[1]])

    def plotDataAcq(self, data, cursorPos):
        self.scopeWidget.clear()
        self.scopeWidget.plot(data, pen='b')
        lr1 = pg.LinearRegionItem([cursorPos[0], cursorPos[1]])
        lr2 = pg.LinearRegionItem([cursorPos[2], cursorPos[3]])
        self.scopeWidget.addItem(lr1)
        self.scopeWidget.addItem(lr2)

    def setCursors(self, cursorPos):
        self.lr1.setRegion([cursorPos[0], cursorPos[1]])
        self.lr2.setRegion([cursorPos[2], cursorPos[3]])

