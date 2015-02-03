from PyQt4 import QtGui
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
        self.scopeWidget.addItem(self.lr1)
        self.scopeWidget.addItem(self.lr2)

    def plotMon(self, data):
        self.lr1.setMovable(True)
        self.lr2.setMovable(True)
        if np.size(self.scopeWidget.listDataItems()) > 0:
           self.scopeWidget.removeItem(self.scopeWidget.listDataItems()[0])
        self.scopeWidget.plot(data, pen=pg.mkPen('k', width=1.2))

        lr1Ret = self.lr1.getRegion()
        lr2Ret = self.lr2.getRegion()
        return np.array([lr1Ret[0], lr1Ret[1], lr2Ret[0], lr2Ret[1]])

    def plotDataAcq(self, data, cursorPos):
        self.scopeWidget.plot(data, pen=pg.mkPen('k', width=1), clear=True)
        self.lr1 = pg.LinearRegionItem([cursorPos[0], cursorPos[1]], brush=pg.mkBrush(0,0,160,80))
        self.lr2 = pg.LinearRegionItem([cursorPos[2], cursorPos[3]], brush=pg.mkBrush(52,124,23,80))
        self.lr1.setMovable(False)
        self.lr2.setMovable(False)
        self.scopeWidget.addItem(self.lr1)
        self.scopeWidget.addItem(self.lr2)

    def setCursors(self, cursorPos):
        self.lr1.setRegion([cursorPos[0], cursorPos[1]])
        self.lr2.setRegion([cursorPos[2], cursorPos[3]])

