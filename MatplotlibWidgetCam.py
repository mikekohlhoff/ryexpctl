from PyQt4.QtCore import *
from PyQt4.QtGui import *

from matplotlib.backend_bases import key_press_handler
from matplotlib.backends.backend_qt4agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)

from matplotlib.figure import Figure
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import math
from pylab import *
import numpy as np

class MplCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure(figsize=(6,10))
        self.ax = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)

class MatplotlibWidgetCam(QGraphicsView):
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        self.canvas = MplCanvas()
        self.vbl = QVBoxLayout()
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)
        self.canvas.fig.patch.set_alpha(0)
        self.canvas.ax.set_axis_off()
        self.savePath = 'C:\\Users\\tpsgroup\\Desktop\\Documents\\Data Mike\\Raw Data\\2015'
        self.cmap = plt.cm.bone

    def plot(self, img):
        self.canvas.ax.clear()
        print 'Img Display'
        #self.ax.imshow(img)
        #self.axCam.imshow(self.lastImage, cmap = self.cmap)#, vmin=450, vmax=650)
        #print self.lastImage.min()
        #print self.lastImage.max()
        
    def saveImg(self):
        savepath = QFileDialog.getSaveFileName(self, 'Save Image to File', self.savePath, 'Image Files(*.pdf *.png)')
        if not savepath: return
        #self.canvas.fig.savefig(str(savepath))
  