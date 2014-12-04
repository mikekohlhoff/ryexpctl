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

# hardware controller modules
from Instruments.PCI7300ADIOCard import *
from Instruments.LeCroyScopeController import LeCroyScopeController
from Instruments.WaveformPotentials import WaveformPotentials21Elec
from multiprocessing import Pipe, Process
import gobject

class RSDControl(QtGui.QMainWindow, ui_form):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.initHardware()
        self.initUI()
        # connect to acq loop, parent connection, child connection
        self.timer = QtCore.QTimer();
        self.scopeActive = False
        self.scanMode = False
        self.tagEvSrc = {}
        self.pipe, pipe = Pipe()
        self.acqLoop = Process(target=self.acquisitionLoop, args=(pipe,))
        self.acqLoop.daemon = True
        self.acqLoop.start()

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
        self.btn_wfOutput.setEnabled(False)
        self.btn_startDataAcq.clicked.connect(self.btn_startDataAcq_clicked)
        self.chk_readScope.clicked.connect(self.chk_readScope_clicked)
        self.inp_voltExtract.editingFinished.connect(self.inp_voltExtract_changed)

        self.setWindowTitle('RSD Control Electronics Test')    
        self.centerWindow()
        self.show()

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
        if self.chk_plotWF.checkState():
            self.plotWFPotentials()

    def reconfigureDIOCard(self):
        self.DIOCard.changeSampleRate(self.inp_sampleRate.value()*1E6)
        self.DIOCard.configureCard(self.chk_extTrig.checkState())
        self.setPCBPotentials()

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

        if self.chk_plotWF.checkState():
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
        # waveform generator
        self.DIOCard = DIOCardController()
        # card configured with 20MHz (sampleRate)
        self.DIOCard.configureCard(self.chk_extTrig.checkState())
        # scope
        self.scope = LeCroyScopeController()
        self.scope.initialize()

    def acquisitionLoop(self,pipe):
        # handle acquisition of scope data
        self.scope.armScope()
        self.scope.setScales()
        acquireData = False
        while True:
            if pipe.poll():
                msg = pipe.recv()
                print 'Scope read status: ', msg
                if msg[0] == 'QUIT SCOPE READ':
                    break
                elif msg[0] == 'MONITOR SCOPE':
                    acquireData = msg[1]
                elif msg[0] == 'DATA ACQ':
                    acquireData = msg[1]
                else:
                    print 'unknown command'

            if acquireData:
                data = self.scope.armwaitread()
                pipe.send(data)
            else:
                time.sleep(.1)

    def chk_readScope_clicked(self):
        self.scanMode = False
        self.startAcquisition()

    def btn_startDataAcq_clicked(self):
        self.scanMode = True
        # reset recorded data
        self.DataDisplay.canvas.ax.clear()
        self.DataDisplay.intgrTrace = []
        if self.chk_readScope.checkState():
            self.scopeActive = False
            self.chk_readScope.setCheckState(QtCore.Qt.Unchecked)
        self.startAcquisition()
        
    def startAcquisition(self):
        if not(self.scanMode) and self.scopeActive:
            self.pipe.send(['MONITOR SCOPE', False])
            self.timer.stop()
            self.disconnect(self.timer,QtCore.SIGNAL("timeout()"), self.acquisitionCtl)
            self.scopeActive = False
        elif not(self.scanMode) and not(self.scopeActive):
            self.pipe.send(['MONITOR SCOPE', True])
            self.connect(self.timer,QtCore.SIGNAL("timeout()"), self.acquisitionCtl)
            self.timer.start(100)
            self.scopeActive = True
        elif self.scanMode and self.scopeActive:
            self.pipe.send(['DATA ACQ', False])
            self.timer.stop()
            self.disconnect(self.timer,QtCore.SIGNAL("timeout()"), self.acquisitionCtl)
            self.btn_startDataAcq.setText('Start Data Acq')
            self.chk_readScope.setEnabled(True)
            self.scopeActive = False
        elif self.scanMode and not(self.scopeActive):
            self.pipe.send(['DATA ACQ', True])
            self.inp_aveSweeps.setValue(1)
            self.connect(self.timer,QtCore.SIGNAL("timeout()"), self.acquisitionCtl)
            self.btn_startDataAcq.setText('Stop Data Acq')
            self.chk_readScope.setEnabled(False)
            self.timer.start(100)
            self.scopeActive = True
        
    def acquisitionCtl(self):
        if self.pipe.poll():
            data = self.pipe.recv()
            self.ScopeDisplay.plot(data)
            if self.scanMode:
                self.DataDisplay.plot(data)
        return True

    def inp_voltExtract_changed(self):pass
    
    def shutDownExperiment(self):
        print 'Release controllers'
        self.pipe.send(["QUIT SCOPE READ"])
        if self.scopeActive:
            self.pipe.recv()
            self.pipe.close()
            self.acqLoop.join()



if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    
    myapp = RSDControl()
    #myapp.initHardware()

    sys.exit(app.exec_())


