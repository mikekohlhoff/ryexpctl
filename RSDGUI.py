import time
from datetime import datetime
import os
import sys

PROJECT_ROOT_DIRECTORY = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0]))))

# UI related
from PyQt4 import QtCore, QtGui, uic
ui_form = uic.loadUiType("rsdgui.ui")[0]

# integrating matplotlib figures
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import random
import numpy as np

# hardware controller modules
from Instruments.PCI7300ADIOCard import *
from Instruments.LeCroyScopeController import LeCroyScopeController
from Instruments.WaveformPotentials import WaveformPotentials21Elec
from Instruments.DCONUSB87P4 import USB87P4Controller

# subclass qthread (not recommended officially, old style)
class scopeThread(QtCore.QThread):

    def __init__(self, scopeActive=True, scope=None):
        QtCore.QThread.__init__(self)
        self.scopeActive = scopeActive
        self.scope = scope
        self.scope.setScales()
        print 'SCOPE THREAD INITIALISED'

    dataReady = QtCore.pyqtSignal(object)
    # override
    def __del__(self):
        self.wait()

    def run(self):
        while self.scopeActive:
            data = self.scope.armwaitread()
            self.dataReady.emit(data)
        #self.quit()
        return

class RSDControl(QtGui.QMainWindow, ui_form):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.initHardware()
        self.initUI()
        
        self.scopeMon = False
        self.scanMode = False

    def initUI(self):
        # iniatilize program with guiding mode parameters
        self.inp_aveSweeps.setValue(1)
        self.inp_initVel.setValue(700)
        self.inp_finalVel.setValue(700)
        self.inp_sampleRate.setValue(self.DIOCard.SampleRate*1E-6)
        self.inp_inTime.setValue(0)
        # distance between first and last 'stable' minima
        self.decelDist = 19.1
        self.outDist = 23.5 - 2.2 - self.decelDist
        self.inp_outDist.setValue(self.outDist)
        self.setPCBPotentials()

        # signals and slots
        self.inp_aveSweeps.editingFinished.connect(self.inp_aveSweeps_changed)
        self.inp_initVel.editingFinished.connect(self.setPCBPotentials)
        self.inp_finalVel.editingFinished.connect(self.setPCBPotentials)
        self.inp_inTime.editingFinished.connect(self.setPCBPotentials)
        self.inp_outDist.editingFinished.connect(self.setPCBPotentials)
        self.inp_sampleRate.editingFinished.connect(self.reconfigureDIOCard)
        self.btn_wfOutput.clicked.connect(self.btn_wfOutput_clicked)
        self.chk_extTrig.stateChanged.connect(self.chk_extTrig_changed)
        self.btn_startDataAcq.clicked.connect(self.btn_startDataAcq_clicked)
        self.chk_readScope.clicked.connect(self.chk_readScope_clicked)
        self.chk_editWF.clicked.connect(self.showWFDisplay)
        self.inp_gate1Start.editingFinished.connect(self.redrawScopeWidget)
        self.inp_gate1Stop.editingFinished.connect(self.redrawScopeWidget)
        self.inp_gate2Start.editingFinished.connect(self.redrawScopeWidget)
        self.inp_gate2Stop.editingFinished.connect(self.redrawScopeWidget)
        # function in module as slot
        self.inp_voltExtract.editingFinished.connect(lambda: self.analogIO.writeAOExtraction(self.inp_voltExtract.value()))
        self.inp_voltOptic1.editingFinished.connect(lambda: self.analogIO.writeAOIonOptic1(self.inp_voltOptic1.value()))
        self.inp_voltMCP.editingFinished.connect(lambda: self.analogIO.writeAOMCP(self.inp_voltMCP.value()))
        self.inp_voltPhos.editingFinished.connect(lambda: self.analogIO.writeAOPhos(self.inp_voltPhos.value()))
        # defaults
        self.radio_voltMode.setChecked(True)
        self.chk_extTrig.setChecked(True)
        self.cursorPosOld = np.array([0,0,0,0])
        self.cursorPos = self.cursorPosOld
        
        self.setWindowTitle('RSD Control Electronics Test')    
        self.centerWindow()
        self.resize(736, 620)
        self.show()

    def chk_readScope_clicked(self):
        self.scopeMon = self.chk_readScope.isChecked()
        if self.scanMode:
            return
        else:    
            if self.scopeMon:
                self.startAcquisitionThread()
                self.enableControlsScope(False)
                self.scope.dispOff()
            else:
                self.scopeThread.scopeActive = False
                self.enableControlsScope(True)
                self.scope.dispOn()

    def btn_startDataAcq_clicked(self):
        self.scanMode = not(self.scanMode)
        if self.scopeMon and hasattr(self, 'scopeThread'):
            self.scopeThread.scopeActive = False
        if self.scanMode:
            self.inp_aveSweeps.setValue(1)
            self.scope.armScope()
            # reset recorded data
            self.DataDisplay.canvas.ax.clear()
            self.DataDisplay.intgrTrace = []
            self.btn_startDataAcq.setText('Stop Data Acq')
            self.scopeMon = True
            self.chk_readScope.setChecked(True)
            self.startAcquisitionThread()
            self.radio_voltMode.setEnabled(False)
            self.radio_wlMode.setEnabled(False)
            self.scope.dispOff()
            print 'DATA ACQ ON'
        else:
            self.scopeThread.scopeActive = False
            self.btn_startDataAcq.setText('Start Data Acq')
            self.scopeMon = False
            self.chk_readScope.setChecked(False)
            self.radio_voltMode.setEnabled(True)
            self.radio_wlMode.setEnabled(True)
            self.scope.dispOn()
            print 'DATA ACQ OFF'

    def startAcquisitionThread(self):
        self.scopeThread = scopeThread(True,self.scope)
        self.scopeThread.scopeActive = True
        self.scopeThread.dataReady.connect(self.acquisitionCtl)
        self.scopeThread.start()

    def acquisitionCtl(self, data):
        if self.scopeMon:pass
            #self.ScopeDisplay.plot(data, self.cursorPos)
        if self.scanMode:
            if self.radio_voltMode.isChecked():
                self.DataDisplay.plot(data, 'volt')
            elif self.radio_wlMode.isChecked():
                self.DataDisplay.plot(data, 'wl')

    def enableControlsScope(self, boolEnbl):
        self.inp_gate1Start.setEnabled(boolEnbl)
        self.inp_gate1Stop.setEnabled(boolEnbl)
        self.inp_gate2Start.setEnabled(boolEnbl)
        self.inp_gate2Stop.setEnabled(boolEnbl)

    def setPCBPotentials(self):
        # 10bit resolution per channel
        maxAmp = 1023/2.0
        self.wfPotentials = WaveformPotentials21Elec()
        vInit = self.inp_initVel.value()
        vFinal = self.inp_finalVel.value()

        # deceleration to stop at fixed position, 19.1 for 23 electrodes
        inTime = self.inp_inTime.value()
        # space beyond minima position after chirp sequence
        # inDist = 2.2mm to first minima with electrods 1&4=Umax
        # if outDist=0 end point of potential sequence 
        # at z position before potential minima diverges
        self.outDist = self.inp_outDist.value()
        outTime = self.outDist*1E-3/vFinal*1E6
        self.inp_outTime.setValue(outTime)
        
        # build waveform potentials
        self.wfPotentials.generate(self.DIOCard.timeStep, vInit, vFinal, inTime, outTime, maxAmp, self.decelDist)
        if self.chk_editWF.checkState():
            self.plotWFPotentials()

    def redrawScopeWidget(self):
        self.cursorPos = np.array([self.inp_gate1Start.value(), self.inp_gate1Stop.value(), \
                     self.inp_gate2Start.value(), self.inp_gate2Stop.value()])
        if (self.cursorPos != self.cursorPosOld).all():
            self.ScopeDisplay.redraw(self.cursorPos)
        self.cursorPosOld = self.cursorPos

    def reconfigureDIOCard(self):
        self.DIOCard.changeSampleRate(self.inp_sampleRate.value()*1E6)
        self.DIOCard.configureCard(self.chk_extTrig.checkState())
        self.setPCBPotentials()

    def showWFDisplay(self):
        if self.chk_editWF.checkState():
            self.resize(736,958)
        else:
            self.resize(736,620)
    
    def plotWFPotentials(self):
        self.WaveformDisplay.plot(self.wfPotentials)
           
    def centerWindow(self):
        frm = self.frameGeometry()
        win = QtGui.QDesktopWidget().availableGeometry().center()
        frm.moveCenter(win)
        self.move(frm.topLeft())

    def inp_aveSweeps_changed(self):
        self.scope.setSweeps(self.inp_aveSweeps.value())

    def btn_wfOutput_clicked(self):
        # check if potentials were created
        if not hasattr(self.wfPotentials, 'potentialsOut'):
            print 'No waveform potentials created'
            return

        if self.chk_editWF.checkState():
            print self.DIOCard.writeWaveformPotentials(self.wfPotentials.potentialsOut)
        else:
           pass

    def chk_extTrig_changed(self):
        self.DIOCard.configureCard(self.chk_extTrig.checkState())
        if self.chk_extTrig.checkState():
            self.btn_wfOutput.setEnabled(False)
        else:
            self.btn_wfOutput.setEnabled(True)

    def closeEvent(self, event):
        reply = QtGui.QMessageBox.question(self, '',
            "Shut down experiment control?", QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)

        if reply == QtGui.QMessageBox.Yes:
            event.accept()
            self.shutDownExperiment()
        else:
            event.ignore()

    def initHardware(self):
        print 'Initialising hardware'
        # connect to lasers
        
        # USB analog input/output
        self.analogIO = USB87P4Controller()
        self.analogIO.openDevice()
        # waveform generator
        self.DIOCard = DIOCardController()
        time.sleep(2)
        # card configured with 20MHz (sampleRate)
        self.DIOCard.configureCard(self.chk_extTrig.checkState())
        # scope
        self.scope = LeCroyScopeController()
        self.scope.initialize()
        print '-----------------------------------------------------------------------------'

    def shutDownExperiment(self):
        print 'Release controllers'
        self.analogIO.closeDevice()
        if hasattr(self, 'scopeThread'):
            self.scopeThread.terminate() # vs exit() vs quit()


if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    
    myapp = RSDControl()
    app.setStyle('plastique')
    app.exec_()
#    sys.exit(app.exec_())


