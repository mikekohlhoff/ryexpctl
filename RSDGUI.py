import sys

# UI related
from PyQt4 import QtCore, QtGui, uic
ui_form = uic.loadUiType("rsdgui.ui")[0]

# integrating matplotlib figures
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import random


# hardware 
from Instruments.PCI7300ADIOCard import *
from Instruments.LeCroyScopeController import *


class RSDControl(QtGui.QMainWindow, ui_form):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.initUI()
        self.initHardware()


    def initUI(self):
        self.setupUi(self)
        self.inp_aveSweeps.editingFinished.connect(self.inp_aveSweeps_changed)
        self.inp_initVel.editingFinished.connect(self.inp_initVel_changed)
        self.inp_finalVel.editingFinished.connect(self.inp_finalVel_changed)

        self.btn_wfOutput.clicked.connect(self.btn_wfOutput_clicked)
        self.chk_extTrig.stateChanged.connect(self.chk_extTrig_changed)

        self.setWindowTitle('RSD Control Electronics Test')    
        self.setWindowIcon(QtGui.QIcon('Janne.png'))
        self.centerWindow()
        self.show()

    def PlotFunc(self):
        self.WaveformDisplay.canvas.ax.clear()
        self.WaveformDisplay.canvas.ax.set_title('PCB Potentials')
        self.WaveformDisplay.canvas.ax.set_xlabel('Time ($\mu$s)')
        self.WaveformDisplay.canvas.ax.set_ylabel('Amplitude (V)')
        self.WaveformDisplay.canvas.fig.patch.set_alpha(0)


        randomNumbers = random.sample(range(0, 10), 10)
        self.WaveformDisplay.canvas.ax.plot(randomNumbers)
        self.ScopeDisplay.canvas.ax.plot(randomNumbers)

        self.WaveformDisplay.canvas.draw()
        self.ScopeDisplay.canvas.draw()
        
    def centerWindow(self):
        frm = self.frameGeometry()
        win = QtGui.QDesktopWidget().availableGeometry().center()
        frm.moveCenter(win)
        self.move(frm.topLeft())
        

    def initHardware(self):
        # waveform generator
        self.DIOCard = DIOCardController()
        print self.DIOCard._DIOCardController__SampleRate
        print self.DIOCard._DIOCardController__timeStep
        self.DIOCard.setWaveformPotentials(700,700, False)

        # scope
        self.scope = LeCroyScopeController()
        self.scope.initialize()
        
    def inp_aveSweeps_changed(self):
        self.scope.setSweeps(self.inp_aveSweeps.value())

    def inp_initVel_changed(self):
        print self.inp_initVel.value()

    def inp_finalVel_changed(self):
        print self.inp_finalVel.value()

    def btn_wfOutput_clicked(self):
    #    self.sys.exit(app.exec_())
        if self.chk_plotWF.checkState():
            #self.PlotFunc()
            self.DIOCard.generateWaveformPotentials
        else:
           pass
    
    def chk_extTrig_changed(self):
        self.DIOCard.configureCard(self.chk_extTrig.checkState())
        
    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, '',
            "Shut down experiment control?", QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()        
        

    def shutDown(self):
        print 'Release controllers'


if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    
    myapp = RSDControl()
    #myapp.initHardware()

    sys.exit(app.exec_())
