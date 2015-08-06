'''
Control RSE experiment, GUI in RSDControl class, scope read-out in separate thread that emits data to widget
that handles data evaluation, display and saving
''' 

import time
from datetime import datetime
import os
import sys

PROJECT_ROOT_DIRECTORY = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0]))))

# UI related
from PyQt4 import QtCore, QtGui, uic
ui_form = uic.loadUiType("rsdgui.ui")[0]
ui_form_waveform = uic.loadUiType("rsdguiWfWin.ui")[0]

# integrating matplotlib figures
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import random
import numpy as np

# hardware controller modules
from Instruments.PCI7300ADIOCard import *
from Instruments.LeCroyScopeController import LeCroyScopeControllerVISA
from Instruments.LeCroyScopeController import LeCroyScopeControllerDSO
from Instruments.WaveformPotentials import WaveformPotentials21Elec
from Instruments.DCONUSB87P4 import USB87P4Controller
from Instruments.PfeifferMaxiGauge import MaxiGauge
from Instruments.QuantumComposerPulseGenerator import PulseGeneratorController

class RSDControl(QtGui.QMainWindow, ui_form):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.initHardware()
        # monitor constants, hasattr(thread) only works before first creation
        self.scopeMon = False
        self.scanMode = False
        self.pressThread = False
        # waveform generation window
        self.WfWin = waveformWindow(self.DIOCard)
        self.initUI()

    def initUI(self):
        # signals and slots
        self.inp_aveSweeps.editingFinished.connect(self.inp_aveSweeps_changed)
        self.btn_startDataAcq.clicked.connect(self.btn_startDataAcq_clicked)
        self.chk_readScope.clicked.connect(self.chk_readScope_clicked)
        self.chk_invertTrace1.clicked.connect(self.chk_invertTrace1_clicked)
        self.chk_invertTrace2.clicked.connect(self.chk_invertTrace2_clicked)
        self.chk_editWF.clicked.connect(self.showWfWin)
        self.chk_readMainGauge.clicked.connect(self.readGauge_clicked)
        self.chk_readSourceGauge.clicked.connect(self.readGauge_clicked)
        self.inp_gate1Start.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate1Stop.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate2Start.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate2Stop.valueChanged.connect(self.setCursorsScopeWidget)
        
        # function in module as slot
        self.inp_voltExtract.editingFinished.connect(lambda: self.analogIO.writeAOExtraction(self.inp_voltExtract.value()))
        self.inp_voltOptic1.editingFinished.connect(lambda: self.analogIO.writeAOIonOptic1(self.inp_voltOptic1.value()))
        self.inp_voltMCP.editingFinished.connect(lambda: self.analogIO.writeAOMCP(self.inp_voltMCP.value()))
        self.inp_voltPhos.editingFinished.connect(lambda: self.analogIO.writeAOPhos(self.inp_voltPhos.value()))
        self.WfWin.winClose.connect(lambda: self.chk_editWF.setEnabled(True))
        self.WfWin.winClose.connect(lambda: self.chk_editWF.setChecked(False))
        self.chk_Excimer.stateChanged.connect(lambda: self.pulseGen.switchChl(2, self.chk_Excimer.isChecked()))
        self.chk_LaserUV.stateChanged.connect(lambda: self.pulseGen.switchChl(5, self.chk_LaserUV.isChecked()))
        self.chk_LaserVUV.stateChanged.connect(lambda: self.pulseGen.switchChl(4, self.chk_LaserVUV.isChecked()))
        self.chk_PulseValve.stateChanged.connect(lambda: self.pulseGen.switchChl(1, self.chk_PulseValve.isChecked()))
        self.ScopeDisplay.line1.sigPositionChanged.connect(lambda: self.inp_extractDelay.setValue(self.ScopeDisplay.line1.value()*1E6))
        self.ScopeDisplay.line1.sigPositionChangeFinished.connect(lambda: self.pulseGen.setDelay(6, float(('{:1.10f}').format(self.inp_extractDelay.value()*1E-6))))
        self.inp_extractDelay.editingFinished.connect(lambda: self.ScopeDisplay.line1.setValue(self.inp_extractDelay.value()*1E-6))
        self.inp_extractDelay.editingFinished.connect(lambda: self.pulseGen.setDelay(6, float(('{:1.10f}').format(self.inp_extractDelay.value()*1E-6))))

        # defaults
        self.inp_aveSweeps.setValue(1)
        self.cursorPos = np.array([0,0,0,0])
        # have only scope non-scan related controls activated
        self.enableControlsScan(True)
        self.groupBox_DataAcq.setEnabled(False)
        self.tabWidget_ScanParam.setEnabled(False)
        self.groupBox_TOF.setEnabled(False)
        self.out_readMainGauge.setText('Gauge turned off')
        self.out_readSourceGauge.setText('Read out not active')

		 # set size of window
        self.setWindowTitle('RSDRSE Control')
        #self.centerWindow()
        #self.setFixedSize(720, 558)
        #self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.show()

    def showWfWin(self):
        '''display control window for decelerator waveform generation'''
        self.chk_editWF.setEnabled(False)
        self.WfWin.show()

    def chk_readScope_clicked(self):
        '''create scope thread and _run()'''
        self.scopeMon = self.chk_readScope.isChecked()
        if self.scopeMon:
            # have scope connection within scope thread
            self.scope.closeConnection()
            self.dataBuf = []
            self.scopeThread = scopeThread(True, self.inp_aveSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority)   
            self.enableControlsScope(True)
            self.ScopeDisplay.line1.setValue(self.inp_extractDelay.value()*1E-6)
        else:
            self.scopeThread.scopeRead = False
            self.enableControlsScope(False)
            self.scope = LeCroyScopeControllerVISA()

    def btn_startDataAcq_clicked(self):
        self.scanMode = not(self.scanMode)
        if self.scanMode:
            # start scan, reset recorded data
            self.scanParam = str(self.scanModeSelect.currentText())
            self.DataDisplay.plotTrace1 = []
            self.DataDisplay.plotTrace2 = []
            self.DataDisplay.errTrace1 = []
            self.DataDisplay.errTrace2 = []
            self.btn_startDataAcq.setText('Abort Data Acq')
            self.enableControlsScan(False)
            print 'DATA ACQ ON'
        else:
            # abort scan
            self.btn_startDataAcq.setText('Start Data Acq')
            self.enableControlsScan(True)
            print 'DATA ACQ OFF'

    def dataAcquisition(self, data):
        # add data
        self.dataBuf.append(data)
        self.cursorPos = self.ScopeDisplay.getCursors()         
        self.setGateField(self.cursorPos)
        if len(self.dataBuf) >= self.scopeThread.avgSweeps:
            # deque trace buffer when average shots is reached
            dataIn = self.dataBuf[0:self.scopeThread.avgSweeps]
            del self.dataBuf[0:self.scopeThread.avgSweeps]
            # integration done in widgets
            if self.scopeMon and not(self.scanMode):
                self.ScopeDisplay.plotMon(dataIn, self.scopeThread.scope.timeincrC1)      
            elif self.scopeMon and self.scanMode:
                self.ScopeDisplay.plotDataAcq(dataIn, self.cursorPos, self.scopeThread.scope.timeincrC1)
                self.DataDisplay.plot(dataIn, self.cursorPos, self.scanParam, self.scopeThread.scope.timeincrC1)
        
    def setGateField(self, cursorPos):
        # convert to mus
        cursorPos = np.around(1E6*cursorPos, decimals=2)
        inpPos = np.array([self.inp_gate1Start.value(), self.inp_gate1Stop.value(), \
                      self.inp_gate2Start.value(), self.inp_gate2Stop.value()])
        if np.array_equal(cursorPos, inpPos):
            return
        else:
            self.inp_gate1Start.setValue(cursorPos[0])
            self.inp_gate1Stop.setValue(cursorPos[1])
            self.inp_gate2Start.setValue(cursorPos[2])
            self.inp_gate2Stop.setValue(cursorPos[3])

    def setCursorsScopeWidget(self):
        cursorPos = np.array([self.inp_gate1Start.value(), self.inp_gate1Stop.value(), \
                                self.inp_gate2Start.value(), self.inp_gate2Stop.value()])
        self.ScopeDisplay.setCursors(1E-6*cursorPos)
           
    def centerWindow(self):
        frm = self.frameGeometry()
        win = QtGui.QDesktopWidget().availableGeometry().center()
        frm.moveCenter(win)
        self.move(frm.topLeft())
        
    def enableControlsScan(self, boolEnbl):
        # lock controls when scanning to avoid DAU to interfere with measurement
        self.tabWidget_ScanParam.setEnabled(boolEnbl)
        self.groupBox_Laser.setEnabled(boolEnbl)
        self.groupBox_MCP.setEnabled(boolEnbl)
        self.groupBox_Extraction.setEnabled(boolEnbl)
        self.groupBox_Scope.setEnabled(boolEnbl)
        self.groupBox_DevControl.setEnabled(boolEnbl)      
        self.groupBox_TOF.setEnabled(boolEnbl)      
        self.groupBox_Decelerator.setEnabled(boolEnbl)
    
    def enableControlsScope(self, boolEnbl):
        # when starting up scan controls locked, only when scope read out activated
        self.groupBox_DataAcq.setEnabled(boolEnbl)
        self.tabWidget_ScanParam.setEnabled(boolEnbl)
        self.groupBox_TOF.setEnabled(boolEnbl)
        
    def inp_aveSweeps_changed(self):
        # sets avg on scope or avg in data eval after readout
        if self.scopeMon:
            self.scopeThread.avgSweepsChanged(self.inp_aveSweeps.value())
        else:
            self.scopeThread.avgSweeps = self.inp_aveSweeps.value()
            # reset data buffer
            self.dataBuf = []  
    
    def chk_invertTrace1_clicked(self):
        if not(self.scopeMon): self.scope.invertTrace('C1', self.chk_invertTrace1.isChecked())
            
    def chk_invertTrace2_clicked(self):
        if not(self.scopeMon): self.scope.invertTrace('C2', self.chk_invertTrace2.isChecked())
            
    def readGauge_clicked(self):
        '''create maxi gauge thread and _run()'''
        # create controller connection within scope thread
        MainActive = self.chk_readMainGauge.isChecked()
        SourceActive = self.chk_readSourceGauge.isChecked()
        if MainActive: MainState = 'ON'
        else: MainState = 'OFF'       
        if not(self.pressThread):
            self.PressureThread = PressureThread(True, MainState)
            self.PressureThread.pressReadReady.connect(self.setPressRead)
            self.PressureThread.start(priority=QtCore.QThread.LowPriority)
            self.pressThread = True
        else:
            self.PressureThread.MainState = MainState            
        if not(MainActive) and not(SourceActive):
            self.pressThread = False
            time.sleep(2)        
            self.PressureThread.ReadActive = False    
        if not(MainActive):
            self.out_readMainGauge.setText('Gauge turned off')
        if not(SourceActive):
            self.out_readSourceGauge.setText('Read out not active')
            
    def setPressRead(self, pressRead):
        if self.chk_readMainGauge.isChecked():
            self.out_readMainGauge.setText(pressRead[0])
        if self.chk_readSourceGauge.isChecked():
            self.out_readSourceGauge.setText(pressRead[1])
            
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
        print '-----------------------------------------------------------------------------'
        print 'Initialising hardware'
        # USB analog input/output
        self.analogIO = USB87P4Controller()
        self.analogIO.openDevice()
        # waveform generator
        self.DIOCard = DIOCardController()
        self.DIOCard.configureCardDO()
        # scope init here for calib and WFSU,
        # conncection closed when scope read-out active
        self.scope = LeCroyScopeControllerVISA()
        #TODO self.scope.initialize()
        self.scope.invertTrace('C1', True)
        self.pulseGen = PulseGeneratorController()
        self.pulseGen.screenUpdate('ON')
        time.sleep(0.1)
        self.inp_extractDelay.setValue(float(self.pulseGen.readDelay(6))*1E6)
        print '-----------------------------------------------------------------------------'

    def shutDownExperiment(self):
        print 'Releasing controllers:'
        self.analogIO.closeDevice()
        self.DIOCard.releaseCard()
        if hasattr(self, 'scopeThread'):
            self.scopeThread.scopeRead = False
            time.sleep(.2)
            self.scopeThread.terminate()
        if hasattr(self, 'scope'):
            self.scope.closeConnection()            
        if hasattr(self.WfWin, 'wfThread'):
            self.WfWin.wfThread.terminate()
        if hasattr(self, 'PressureThread'):
            self.PressureThread.terminate()
        if hasattr(self, 'pulseGen'):
            self.pulseGen.closeConnection()
        self.WfWin.close()
        
# subclass qthread (not recommended officially, old style)
class PressureThread(QtCore.QThread):
    def __init__(self, ReadActive, MainState):
        QtCore.QThread.__init__(self)
        self.ReadActive = ReadActive
        self.MainState = MainState
        self.MaxiGauge = MaxiGauge('COM1')
        
    pressReadReady = QtCore.pyqtSignal(object)
    
    def __del__(self):
        self.wait()
        
    def run(self):
        while self.ReadActive:
            self.MaxiGauge.gaugeSwitch(4, self.MainState)
            self.msleep(100)
            ps = self.MaxiGauge.pressures()
            MainPress = "{:2.3e} mbar".format(ps[3].pressure)
            SourcePress = "{:2.3e} mbar".format(ps[0].pressure)
            self.pressReadReady.emit([MainPress, SourcePress])
        self.MaxiGauge.disconnect()
        self.quit()
        return
      
class scopeThread(QtCore.QThread):
    def __init__(self, scopeRead=True, avgSweeps=1):
        QtCore.QThread.__init__(self)
        self.scopeRead = scopeRead
        self.scope = LeCroyScopeControllerVISA()
        # averages for data eval with single traces from scope
        self.avgSweeps = avgSweeps
        self.scope.invertTrace('C1', False)
        self.scope.setSweeps(1)
        self.scope.setScales()
        print self.scope.trigOffsetC1
        self.accumT = 0
        self.iT = 0
        
    dataReady = QtCore.pyqtSignal(object)
    # override
    def __del__(self):
        self.wait()

    def run(self):
        self.scope.dispOff()
        while self.scopeRead:
            start = time.clock()
            data = self.scope.armwaitread()
            self.dataReady.emit(data)
            self.accumT = self.accumT + (time.clock() - start)*1000
            self.iT = self.iT + 1
            print (self.accumT/self.iT)
        # return control to scope
        self.scope.dispOn()
        self.scope.invertTrace('C1', True)
        self.scope.trigModeNormal()
        self.scope.closeConnection()
        self.quit()
        return
        
    def avgSweepsChanged(self, avgSweeps):
        self.avgSweeps = avgSweeps
        print 'Avg sweeps for data eval changed to ' + str(self.avgSweeps)

class waveformGenThread(QtCore.QThread):
    def __init__(self, wfOutActive, DIOCard=None):
        QtCore.QThread.__init__(self)
        self.wfOutActive = wfOutActive
        self.DIOCard = DIOCard

    def run(self):
        while self.wfOutActive:
            self.DIOCard.writeWaveformPotentials()
            # reset card before next trigger at 10Hz
            self.msleep(50)
        self.quit()
        return
            
class waveformWindow(QtGui.QWidget, ui_form_waveform):
    def __init__(self, DIOCard):
        QtGui.QWidget.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Waveform Control')
        self.setFixedSize(196, 258)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        
        # card configured with 20MHz (sampleRate)
        self.DIOCard = DIOCard
        # iniatilize program with guiding mode parameters
        self.inp_initVel.setValue(700)
        self.inp_finalVel.setValue(700)
        self.inp_sampleRate.setValue(self.DIOCard.SampleRate*1E-6)
        self.inp_inTime.setValue(0)
        # distance between first and last 'stable' minima
        self.decelDist = 19.1
        self.outDist = 23.5 - 2.2 - self.decelDist
        self.inp_outDist.setValue(self.outDist)
        self.setPCBPotentials()
        self.inp_initVel.editingFinished.connect(self.setPCBPotentials)
        self.inp_finalVel.editingFinished.connect(self.setPCBPotentials)
        self.inp_inTime.editingFinished.connect(self.setPCBPotentials)
        self.inp_outDist.editingFinished.connect(self.setPCBPotentials)
        self.inp_sampleRate.setReadOnly(True)
        self.chk_extTrig.stateChanged.connect(self.startDOOutput)
        self.chk_plotWF.stateChanged.connect(self.resizeWfWin)

    winClose = QtCore.pyqtSignal()

    def closeEvent(self, event):
        event.accept()
        self.winClose.emit()

    def startDOOutput(self):
        if hasattr(self, 'wfThread') and self.wfThread.wfOutActive:
            self.wfThread.wfOutActive = False
        else:
            self.wfThread = waveformGenThread(True, self.DIOCard)
            self.wfThread.start(priority=QtCore.QThread.HighestPriority)

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
        self.wfPotentials.generate(self.DIOCard.timeStep, vInit, vFinal, inTime, outTime, \
                                   maxAmp, self.decelDist)
        #if hasattr(self, 'wfThread') and self.wfThread.wfOutActive:
        #    self.wfThread.wfOutActive = False
        #    self.DIOCard.buildDOBuffer(self.wfPotentials.potentialsOut)
        #    self.startDOOutput()
        #else:
        #    self.DIOCard.buildDOBuffer(self.wfPotentials.potentialsOut)
        self.DIOCard.buildDOBuffer(self.wfPotentials.potentialsOut)
        if self.chk_plotWF.checkState():
            self.WaveformDisplay.plot(self.wfPotentials)

    def resizeWfWin(self):
        if self.chk_plotWF.isChecked():
            self.setFixedSize(640, 300)
        else:
            self.setFixedSize(196, 258)

            
if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    myapp = RSDControl()
    app.exec_()
