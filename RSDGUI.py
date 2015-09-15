# -*- coding: utf-8 -*-
'''
Control RSE experiment, GUI in RSDControl class, scope read-out in separate thread that emits data to widget
that handles data evaluation, display and saving
''' 

import time
from datetime import datetime
import os
import sys
import pickle
import math

# UI related
from PyQt4 import QtCore, QtGui, uic
ui_form = uic.loadUiType("rsdgui.ui")[0]
ui_form_waveform = uic.loadUiType("rsdguiWfWin.ui")[0]
ui_form_startmcp = uic.loadUiType("rsdguiStartMCP.ui")[0]

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
from Instruments.SirahLaserControl import SirahLaserController

class RSDControl(QtGui.QMainWindow, ui_form):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.initHardware()
        # monitor constants, hasattr(thread) only works before first creation
        self.scopeMon = False
        self.scanMode = False
        self.gateInt = False
        self.pressThread = False
        self.setPotBool = False
        # if program crashes, reset MCP/Phos analog output
        self.shutdownStatus = [False, 0, 0]
        # waveform generation window
        self.WfWin = waveformWindow(self.DIOCard)
        self.initUI()

    def initUI(self):
        # signals and slots
        self.inp_avgSweeps.editingFinished.connect(self.inp_avgSweeps_changed)
        self.btn_startDataAcq.clicked.connect(self.btn_startDataAcq_clicked)
        self.chk_readScope.clicked.connect(self.chk_readScope_clicked)
        self.chk_invertTrace1.clicked.connect(self.chk_invertTrace1_clicked)
        self.chk_invertTrace2.clicked.connect(self.chk_invertTrace2_clicked)
        self.chk_editWF.clicked.connect(self.showWfWin)
        self.chk_readMainGauge.clicked.connect(self.readGauge_clicked)
        self.chk_readSourceGauge.clicked.connect(self.readGauge_clicked)
        self.chk_gateInt.stateChanged.connect(self.chk_gateInt_stateChanged)
        self.inp_gate1Start.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate1Stop.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate2Start.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate2Stop.valueChanged.connect(self.setCursorsScopeWidget)
        self.ScopeDisplay.line1.sigPositionChanged.connect(self.setExtractionDelay)
        self.inp_extractDelay.editingFinished.connect(self.setExtractionDelay)
        self.btn_startMCP.clicked.connect(self.startMCPPhos)
        self.chk_connectLasers.clicked.connect(self.connectLasers)
        self.inp_voltMCP.valueChanged.connect(self.saveMCPVoltage)
        self.inp_voltPhos.valueChanged.connect(self.saveMCPVoltage)
        
        # function in module as slot
        self.inp_voltExtract.valueChanged.connect(lambda: self.analogIO.writeAOExtraction(self.inp_voltExtract.value()))
        self.inp_voltOptic1.valueChanged.connect(lambda: self.analogIO.writeAOIonOptic1(self.inp_voltOptic1.value()))
        self.inp_voltMCP.valueChanged.connect(lambda: self.analogIO.writeAOMCP(self.inp_voltMCP.value()))
        self.inp_voltPhos.valueChanged.connect(lambda: self.analogIO.writeAOPhos(self.inp_voltPhos.value()))
        self.WfWin.winClose.connect(lambda: self.chk_editWF.setEnabled(True))
        self.WfWin.winClose.connect(lambda: self.chk_editWF.setChecked(False))
        self.chk_Excimer.stateChanged.connect(lambda: self.pulseGen.switchChl(2, self.chk_Excimer.isChecked()))
        self.chk_LaserUV.stateChanged.connect(lambda: self.pulseGen.switchChl(5, self.chk_LaserUV.isChecked()))
        self.chk_LaserVUV.stateChanged.connect(lambda: self.pulseGen.switchChl(4, self.chk_LaserVUV.isChecked()))
        self.chk_PulseValve.stateChanged.connect(lambda: self.pulseGen.switchChl(1, self.chk_PulseValve.isChecked()))
        self.chk_ExtractionPulse.stateChanged.connect(lambda: self.pulseGen.switchChl(6, self.chk_ExtractionPulse.isChecked()))
        self.inp_setWL_UV.editingFinished.connect(lambda: self.setWavelengths('UV'))
        self.inp_setWL_VUV.editingFinished.connect(lambda: self.setWavelengths('VUV'))
        self.scanModeSelect.currentIndexChanged.connect(lambda: self.tabWidget_ScanParam.setCurrentIndex(self.scanModeSelect.currentIndex()))
        self.tabWidget_ScanParam.currentChanged.connect(lambda: self.scanModeSelect.setCurrentIndex(self.tabWidget_ScanParam.currentIndex()))
        self.inp_setDelayLasers.valueChanged.connect(lambda: self.pulseGen.setDelay(4, self.inp_setDelayLasers.value()*1E-6))
        self.inp_setDelayLasers.valueChanged.connect(self.calcRydVelocity)
        
        # defaults
        self.saveFilePath = 'C:\\Users\\tpsadmin\\Desktop\\Documents\\Data Mike\\Raw Data\\2015'
        self.inp_avgSweeps.setValue(1)
        self.cursorPos = np.array([0,0,0,0])
        # have only scope non-scan related controls activated
        self.enableControlsScan(True)
        self.groupBox_DataAcq.setEnabled(False)
        self.tabWidget_ScanParam.setEnabled(False)
        self.groupBox_TOF.setEnabled(False)
        self.out_readMainGauge.setText('Gauge turned off')
        self.out_readSourceGauge.setText('Read out not active')
        self.out_gateInt.setText('Inactive')
        self.inp_setWL_UV.setEnabled(False)
        self.inp_setWL_VUV.setEnabled(False)
        currentIndex=self.tabWidget_ScanParam.currentIndex()
        currentWidget=self.tabWidget_ScanParam.currentWidget()
        self.tabWidget_ScanParam.setCurrentIndex(self.scanModeSelect.currentIndex())
        self.chk_LaserUV.setChecked(True)
        self.chk_LaserVUV.setChecked(True)
        self.chk_Excimer.setChecked(True)
        self.pulseGen.switchChl(1, False)
        self.pulseGen.switchChl(6, False)
        self.inp_setDelayLasers.setValue(float(self.pulseGen.readDelay(4))*1E6)
        self.calcRydVelocity()
        
        # set size of window
        self.setWindowTitle('RSE CONTROL')
        self.centerWindow()
        self.setFixedSize(971, 628)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.show()

    def showWfWin(self):
        '''display control window for decelerator waveform generation'''
        self.chk_editWF.setEnabled(False)
        self.WfWin.show()
        
    def calcRydVelocity(self):
        '''Calculate atom beam velocity by flight time'''
        # thesis Eric 46+/-8cm
        dist = 0.46
        self.out_velMon.setText('{:d}'.format(int((dist/(self.inp_setDelayLasers.value()*1E-6))*math.sin(math.radians(20)))))
        
    def startMCPPhos(self):
        '''display controls to ramp MCP/Phos voltages'''
        self.StartMCPWin = StartMCPWin(self.analogIO, self.inp_voltMCP.value(), self.inp_voltPhos.value())
        self.StartMCPWin.winClose.connect(self.closeStartMCPWin)
        self.StartMCPWin.setTextFinal.connect(self.setVoltText)
        self.StartMCPWin.ctlActive(True)
        self.StartMCPWin.show()
        self.enableControlsScan(False)
        self.groupBox_DataAcq.setEnabled(False)
        self.setPotBool = True
        
    def closeStartMCPWin(self):
        self.enableControlsScan(True)
        self.groupBox_DataAcq.setEnabled(True)
        self.setPotBool = False
        self.saveMCPVoltage()
        
    def setVoltText(self, text):
        self.inp_voltMCP.setValue(int(text[0]))
        self.inp_voltPhos.setValue(int(text[1]))
        
    def saveMCPVoltage(self):
        self.shutdownStatus[1] = self.inp_voltMCP.value()
        self.shutdownStatus[2] =  self.inp_voltPhos.value()
        file = open('storeMCPPhos.pckl', 'w')
        pickle.dump(self.shutdownStatus, file)
        file.close()
        
    def chk_readScope_clicked(self):
        '''create scope thread and _run()'''
        self.scopeMon = self.chk_readScope.isChecked()
        if self.scopeMon:
            file = open('lastGateTimes.pckl')
            lastTimes = pickle.load(file)
            file.close()
            self.inp_gate1Start.setValue(lastTimes[0])
            self.inp_gate1Stop.setValue(lastTimes[1])
            self.inp_gate2Start.setValue(lastTimes[2])
            self.inp_gate2Stop.setValue(lastTimes[3])    
            # have scope connection within scope thread
            self.scope.closeConnection()
            self.dataBuf = []
            self.scopeThread = scopeThread(True, False, self.inp_avgSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority)   
            self.enableControlsScope(True)
            self.chk_invertTrace1.setChecked(False)
            self.ScopeDisplay.lr1.setMovable(True)
            self.ScopeDisplay.lr2.setMovable(True)
            self.ScopeDisplay.line1.setMovable(True)
            self.inp_extractDelay.setValue(float(self.pulseGen.readDelay(6))*1E6)
            self.ScopeDisplay.line1.setValue(self.inp_extractDelay.value()*1E-6 + self.scopeThread.scope.trigOffsetC1)
            print "Scope offset to trigger: " + str(self.scopeThread.scope.trigOffsetC1)
        else:
            self.scopeThread.scopeRead = False
            self.enableControlsScope(False)
            self.chk_invertTrace1.setChecked(True)
            self.scope = LeCroyScopeControllerVISA()
            self.chk_invertTrace1_clicked()
            self.scope.setSweeps(self.inp_avgSweeps.value())
            self.ScopeDisplay.lr1.setMovable(False)
            self.ScopeDisplay.lr2.setMovable(False)
            self.ScopeDisplay.line1.setMovable(False)
            self.chk_gateInt.setChecked(False)

    def btn_startDataAcq_clicked(self):
        # set parameters for dataAcquisition()
        self.scanMode = not(self.scanMode)
        # set last used gate times        
        file = open('lastGateTimes.pckl', 'w')
        pickle.dump([self.inp_gate1Start.value(), self.inp_gate1Stop.value(), \
                  self.inp_gate2Start.value(), self.inp_gate2Stop.value()], file)
        file.close()
        if self.scanMode:
            self.scanMode = False
            if str(self.scanModeSelect.currentText()) == 'Wavelength' and not(self.chk_connectLasers.isChecked()):
                QtGui.QMessageBox.critical(self, 'Sirah Laser Error', "Lasers not connected.", QtGui.QMessageBox.Ok)
                return
            if self.inp_avgSweeps.value() < 2:
                QtGui.QMessageBox.critical(self, 'Data Acquistion Warning', "Average needs to be at least 2.", QtGui.QMessageBox.Ok)
                return
            self.btn_startDataAcq.setText('Abort Data Acq')
            # reconnect to scope to switch display otherwise access problems
            self.scopeThread.scopeRead = False
            time.sleep(0.4)
            # set scan parameters
            self.setScanParams()
            self.scopeThread = scopeThread(True, True, self.inp_avgSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority)
            self.enableControlsScan(False)
            self.line1Pos = self.ScopeDisplay.line1.value()
        else:
            # abort scan
            if 'Wavelength' in self.scanParam:
                self.devParam.CancelBurst()
            self.scopeThread.scopeRead = False
            if len(self.DataDisplay.dataTrace1) > 0:
                self.openSaveFile()
            self.scopeThread = scopeThread(True, False, self.inp_avgSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority) 
            # reset devices to value before scan
            self.btn_startDataAcq.setText('Start Data Acq')
            self.setParam = self.beforescanParam
            self.scanSetDevice()
            self.progressBarScan.setValue(0)
            self.enableControlsScan(True)          
            print 'DATA ACQ OFF'
        
    def setScanParams(self):
        self.scanParam = str(self.scanModeSelect.currentText())
        if self.scanParam == 'Voltage':
            self.scanParam = self.scanParam + ' ' + str(self.voltageSelectScan.currentText())
            self.startParam = self.inp_startField.value()
            self.stopParam = self.inp_stopField.value()
            self.stepParam = self.inp_incrField.value()
            self.setParam = self.startParam
            self.setOutParam = self.out_voltMon
            self.beforescanParam = self.inp_voltExtract.value()
            self.scanSetDevice()            
        elif self.scanParam == 'Wavelength':
            self.scanParam = self.scanParam + ' ' + str(self.laserSelectScan.currentText())
            self.startParam = self.inp_startWL.value()
            self.stopParam = self.inp_stopWL.value()
            self.stepParam = self.inp_incrWL.value()
            self.setParam = self.startParam
            self.setOutParam = self.out_WLMon
            if 'VUV' in self.scanParam:
                self.beforescanParam = self.inp_setWL_VUV.value()
                self.devParam = self.VUVLaser
            else:
                self.beforescanParam = self.inp_setWL_UV.value()
                self.devParam = self.UVLaser
            self.setOutParam.setText(str(self.beforescanParam))
            self.burstStart = LaserBurstThread(self.devParam, self.startParam, self.stopParam, self.stepParam, self.scanParam)
            self.burstStart.burstReady.connect(self.resetDatBuf)
            self.burstStart.start()
        elif 'Delay' in self.scanParam:
            self.scanParam = self.scanParam + ' ' + str(self.delaySelectScan.currentText())
            self.startParam = self.inp_startDelay.value()*1E-6
            self.stopParam = self.inp_stopDelay.value()*1E-6
            self.stepParam = self.inp_incrDelay.value()*1E-6
            self.setParam = self.startParam
            self.setOutParam = self.out_delayMon
            # set delay generator channel for scan
            if 'Rydberg' in self.scanParam:
                # Fire channel
                self.devParam = 4
            elif 'Extract' in self.scanParam:
                # Fire channel
                self.devParam = 6 
            elif 'Photo' in self.scanParam:
                # Fire channel
                self.devParam = 2
            self.beforescanParam = float(self.pulseGen.readDelay(self.devParam))               
            self.scanSetDevice()
        # determine scan direction
        if self.stopParam > self.startParam:
            self.scanDirection = 1
        else:
            self.scanDirection = -1
        # set scan flag in thread
        if not('Wavelength' in self.scanParam):         
            self.resetDatBuf()   

    def resetDatBuf(self):
        #reset recorded data
        self.dataBuf = []
        self.DataDisplay.dataTrace1 = []
        self.DataDisplay.dataTrace2 = []
        self.DataDisplay.errTrace1 = []
        self.DataDisplay.errTrace2 = []
        self.DataDisplay.paramTrace = []
        self.scanMode = True
        print 'DATA ACQ ON'
           
    def dataAcquisition(self, data):
        # add data       
        self.dataBuf.append(data)
        self.cursorPos = self.ScopeDisplay.getCursors()         
        self.setGateField(self.cursorPos)
        if len(self.dataBuf) >= self.scopeThread.avgSweeps and not(self.gateInt):
            # deque trace buffer when average shots is reached
            dataIn = self.dataBuf[0:self.scopeThread.avgSweeps]
            del self.dataBuf[0:self.scopeThread.avgSweeps]
            if self.scopeMon and not(self.scanMode):
                # scope monitor plotting
                self.ScopeDisplay.plotMon(dataIn, self.scopeThread.scope.timeincrC1)                
            elif self.scopeMon and self.scanMode:
                # scan plotting
                self.ScopeDisplay.plotDataAcq(dataIn, self.cursorPos, self.scopeThread.scope.timeincrC1, self.line1Pos)
                self.DataDisplay.plot(dataIn, self.setParam, self.cursorPos, self.scanParam, self.scopeThread.scope.timeincrC1)     
                if self.setParam == self.stopParam:
                    # last data point recorded, save data, reset to value before scan in btn_acq_clicked()
                    self.btn_startDataAcq_clicked()
                else:
                    # step scan parameter
                    if not('Wavelength' in self.scanParam):
                        self.setParam += self.scanDirection*self.stepParam                
                    self.scanSetDevice()                   
        elif self.scopeMon and self.gateInt:
             # gate 1 integration
             # don't deque for < avgSweeps, calculate average and error from whole buffer
            if len(self.dataBuf) > self.scopeThread.avgSweeps:
                del self.dataBuf[0]
            dataIn = self.dataBuf[:]
            data = self.ScopeDisplay.plotMon(dataIn, self.scopeThread.scope.timeincrC1)
            cPos = [round(self.cursorPos[0]/self.scopeThread.scope.timeincrC1), 
                   round(self.cursorPos[1]/self.scopeThread.scope.timeincrC1)]
            self.gateIntVal = sum(data[cPos[0]:cPos[1]])
            # std deviation for average
            dataErr = np.vstack(dataIn)
            err = np.std(dataIn, axis=0)
            # error propagation
            self.gateIntErr = np.sqrt(sum(np.square(err[cPos[0]:cPos[1]])))
            self.out_gateInt.setText('{:.2f} '.format(self.gateIntVal) + QtCore.QString(u'±') + ' {:.2f}'.format(self.gateIntErr))
    
    def scanSetDevice(self):        
        if 'Voltage' in self.scanParam:
            self.analogIO.writeAOExtraction(self.setParam)
            outVal = self.setParam
        elif 'Wavelength' in self.scanParam: 
            # reset laser to former wavelength
            if not self.scanMode and 'UV' in self.scanParam:
                self.setLaser = LaserThread(self.devParam, self.setParam, self.inp_setWL_UV)
                self.setLaser.start()
                self.out_WLMon.setText('{:3.4f}'.format(self.setParam))
                return
            elif not self.scanMode and 'VUV' in self.scanParam:
                self.setLaser = LaserThread(self.devParam, self.setParam, self.inp_setWL_VUV)
                self.setLaser.start()
                self.out_WLMon.setText('{:3.4f}'.format(self.setParam))
                return
            (wl, cont) = self.devParam.NextBurst()    
            self.setParam = float('{:.5f}'.format(wl))
            outVal = '{:3.4f}'.format(wl)
            # if sum(steps) != stop - start
            if not cont: self.setParam = self.stopParam
        elif 'Delay' in self.scanParam:
             self.setParam = float('{:.11f}'.format(self.setParam))
             self.pulseGen.setDelay(self.devParam, float('{:1.11f}'.format(self.setParam)))
             outVal = '{:4.5f}'.format(self.setParam*1E6)
        self.progressBarScan.setValue((float(abs(self.setParam - self.startParam))/abs(self.stopParam - self.startParam))*1E2)
        self.setOutParam.setText(str(outVal))
    
    def openSaveFile(self):
        fileName = self.scanParam + 'Scan' + '{:s}'.format(self.inp_fileName.text()) + time.strftime("%y%m%d") + time.strftime("%H%M")
        filePath = os.path.join(self.saveFilePath, fileName)
        savePath = QtGui.QFileDialog.getSaveFileName(self, 'Save Traces', filePath, '(*.txt)')
        print self.saveFilePath
        saveData = np.hstack((np.vstack(np.asarray(self.DataDisplay.paramTrace)), np.vstack(np.asarray(self.DataDisplay.dataTrace1)), 
                            np.vstack(np.asarray(self.DataDisplay.errTrace1)), np.vstack(np.asarray(self.DataDisplay.dataTrace2)), 
                            np.vstack(np.asarray(self.DataDisplay.errTrace2))))
        if str(savePath):
            self.saveFilePath = os.path.dirname(str(savePath))
            print 'Save data file'
            if 'Voltage' in self.scanParam:
                fmtIn = '%.3f'
            elif 'Wavelength' in self.scanParam:
                # smallest step .00025nm
                fmtIn = '%.5f'
            elif 'Delay' in self.scanParam:
                fmtIn = '%.11f'
            np.savetxt(str(savePath), saveData, fmt=fmtIn, delimiter='\t', newline='\n', header=self.scanParam+(u'\tDat1\tErr1\tDat2\tErr2'),
                      footer='', comments=('# Comment: ' + str(self.inp_fileComment.text()) + '\n'))

    def chk_gateInt_stateChanged(self):
        '''integrate 1 gate to append to data acq file'''
        # set parameters for dataAcquisition()
        self.gateInt = self.chk_gateInt.isChecked()
        if self.gateInt:  
            # get average from scope, not data eval
            self.btn_startDataAcq.setEnabled(False)
            self.out_gateInt.setText('0')
            print 'Integrate TOF gate 1'
        else:
            self.scopeThread.avgSweeps = 1
            self.inp_avgSweeps.setValue(1)
            self.out_gateInt.setText('Inactive')
            self.btn_startDataAcq.setEnabled(True)
                                          
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
     
    def setExtractionDelay(self):
        if self.inp_extractDelay.hasFocus():
            val = self.inp_extractDelay.value()*1E-6
            self.ScopeDisplay.line1.setValue(val + self.scopeThread.scope.trigOffsetC1)
            self.pulseGen.setDelay(6, float(('{:1.11f}').format(val)))
        
    def centerWindow(self):
        frm = self.frameGeometry()
        win = QtGui.QDesktopWidget().availableGeometry().center()
        frm.moveCenter(win)
        self.move(frm.topLeft())
        
    def enableControlsScan(self, boolEnbl):
        # lock controls when scanning to avoid DAU to interfere with measurement
        self.groupBox_Laser.setEnabled(boolEnbl)
        self.groupBox_MCP.setEnabled(boolEnbl)
        self.groupBox_Extraction.setEnabled(boolEnbl)
        self.groupBox_Scope.setEnabled(boolEnbl)
        self.groupBox_DevControl.setEnabled(boolEnbl)      
        self.groupBox_TOF.setEnabled(boolEnbl)      
        self.groupBox_Decelerator.setEnabled(boolEnbl)
        self.scanModeSelect.setEnabled(boolEnbl)
        self.inp_fileName.setEnabled(boolEnbl)
        self.chk_gateInt.setEnabled(boolEnbl)
        self.out_gateInt.setEnabled(boolEnbl)
    
    def enableControlsScope(self, boolEnbl):
        # when starting up scan controls locked, only when scope read out activated
        self.groupBox_DataAcq.setEnabled(boolEnbl)
        self.tabWidget_ScanParam.setEnabled(boolEnbl)
        self.groupBox_TOF.setEnabled(boolEnbl)
        
    def inp_avgSweeps_changed(self):
        # sets avg on scope or avg in data eval after readout
        if self.inp_avgSweeps.hasFocus():
            if not(self.scopeMon):
                self.scope.setSweeps(self.inp_avgSweeps.value())
            else:
                self.scopeThread.avgSweeps = self.inp_avgSweeps.value()
                print 'Avg sweeps for data eval changed to ' + str(self.scopeThread.avgSweeps)
                # reset data buffer
                self.dataBuf = []            
    
    def chk_invertTrace1_clicked(self):
        if not(self.scopeMon): self.scope.invertTrace('C1', self.chk_invertTrace1.isChecked())
            
    def chk_invertTrace2_clicked(self):
        if not(self.scopeMon): self.scope.invertTrace('C2', self.chk_invertTrace2.isChecked())
     
    def connectLasers(self):    
        if self.chk_connectLasers.isChecked():
            self.UVLaser = SirahLaserController('UV')
            if self.UVLaser.OpenLaser():
                QtGui.QMessageBox.warning(self, 'Sirah Laser Error',
                "Close Sirah Control interface for UV laser.", QtGui.QMessageBox.Ok)
                self.laserErr = True
                self.chk_connectLasers.setChecked(False)
                return
            self.VUVLaser = SirahLaserController('VUV')
            if self.VUVLaser.OpenLaser():
                QtGui.QMessageBox.warning(self, 'Sirah Laser Error',
                "Close Sirah Control interface for VUV laser.", QtGui.QMessageBox.Ok)
                self.laserErr = True
                self.chk_connectLasers.setChecked(False)
                self.UVLaser.CloseLaser()
                return
            else:
                self.inp_setWL_UV.setEnabled(True)
                self.inp_setWL_VUV.setEnabled(True)
                self.inp_setWL_UV.setValue(self.UVLaser.GetWavelength())
                self.inp_setWL_VUV.setValue(self.VUVLaser.GetWavelength())
                self.laserErr = False
                
        elif not(self.chk_connectLasers.isChecked()) and not(self.laserErr):         
            self.UVLaser.CloseLaser()
            self.VUVLaser.CloseLaser()
            self.inp_setWL_UV.setEnabled(False)
            self.inp_setWL_VUV.setEnabled(False)
        else: pass
        
    def setWavelengths(self, laser):
        if laser == 'UV' and self.inp_setWL_UV.hasFocus():
            self.setLaser = LaserThread(self.UVLaser, self.inp_setWL_UV.value(), self.inp_setWL_UV)
            self.setLaser.start()
            
        elif laser == 'VUV' and self.inp_setWL_VUV.hasFocus():
            self.setLaser = LaserThread(self.VUVLaser, self.inp_setWL_VUV.value(), self.inp_setWL_VUV)
            self.setLaser.start()
     
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
            self.PressureThread.start()
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
        self.blockSignals(True)
        if not(self.setPotBool):
            reply = QtGui.QMessageBox.question(self, 'RSE Control',
                "Shut down experiment control?", QtGui.QMessageBox.Yes | 
                QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)  
            if reply == QtGui.QMessageBox.Yes:
                event.accept()
                self.shutDownExperiment()
            else:
                event.ignore()
                self.blockSignals(False)
        else:
            event.ignore()

    def initHardware(self):
        print '-----------------------------------------------------------------------------'
        print 'Initialising hardware'
        self.pulseGen = PulseGeneratorController()
        # USB analog input/output
        self.analogIO = USB87P4Controller()
        self.analogIO.openDevice()
        file = open('storeMCPPhos.pckl')
        lastVal = pickle.load(file)
        file.close()
        lastMCP = lastVal[1]
        lastPhos = lastVal[2]
        if lastMCP != 0 or lastPhos != 0:
            reply = QtGui.QMessageBox.question(self, 'RSE Control',
                "Restore MCP and Phosphor screen voltages to {:d}/{:d} (V)?".format(lastMCP, lastPhos), QtGui.QMessageBox.Yes | 
                QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)  
            if reply == QtGui.QMessageBox.Yes:
                self.inp_voltMCP.setValue(lastMCP)
                self.inp_voltPhos.setValue(lastPhos)
                self.analogIO.writeAOMCP(lastMCP)
                self.analogIO.writeAOPhos(lastPhos)
            else: pass
        # waveform generator
        self.DIOCard = DIOCardController()
        self.DIOCard.configureCardDO()
        # scope init here for calib and WFSU,
        # conncection closed when scope read-out active
        self.scope = LeCroyScopeControllerVISA()       
        self.scope.initialize()
        self.scope.invertTrace('C1', True)
        self.chk_invertTrace1.setChecked(True)
        print '-----------------------------------------------------------------------------'
        print 'Initiate Lasers when not Sirah Control interfaces closed'

    def shutDownExperiment(self):
        self.blockSignals(True)
        self.analogIO.writeAOExtraction(0)
        self.analogIO.writeAOIonOptic1(0)
        self.shutdownStatus[0] = True
        self.saveMCPVoltage()
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
        if self.chk_connectLasers.isChecked():
            self.UVLaser.CloseLaser()
            self.VUVLaser.CloseLaser()
        self.WfWin.close()
        
# subclass qthread (not recommended officially, old style)
class scopeThread(QtCore.QThread):
    def __init__(self, scopeRead=True, dispOff=False, avgSweeps=1):
        QtCore.QThread.__init__(self)
        self.scopeRead = scopeRead
        self.scope = LeCroyScopeControllerVISA()
        # averages for data eval with single traces from scope
        self.avgSweeps = avgSweeps
        self.scope.setSweeps(1)
        self.scope.invertTrace('C1', False)
        self.scope.setScales()
        if dispOff:
            self.scope.dispOff()
        
    dataReady = QtCore.pyqtSignal(object)
    # override
    def __del__(self):
        self.wait()

    def run(self):
        #self.scope.dispOff()
        while self.scopeRead:
            data = self.scope.armwaitread()
            self.dataReady.emit(data) 
        # return control to scope
        self.scope.dispOn()
        self.scope.invertTrace('C1', True)
        self.scope.trigModeNormal()
        self.scope.closeConnection()
        self.quit()
        return     
        
class LaserThread(QtCore.QThread):
    '''do goto in thread'''
    def __init__(self, laser, value, disp):
        QtCore.QThread.__init__(self)
        self.laser = laser
        self.value = value
        self.disp = disp
      
    def __del__(self):
        self.wait()

    def run(self):
        self.laser.Goto(self.value)
        self.disp.setValue(self.laser.GetWavelength())
        self.quit()
        return
        
class LaserBurstThread(QtCore.QThread):
    '''do goto in thread'''
    def __init__(self, laser, start, stop, step, dev):
        QtCore.QThread.__init__(self)
        self.laser = laser
        self.startParam = start
        self.stopParam = stop
        self.stepParam = step
        self.dev = dev
    burstReady = QtCore.pyqtSignal() 
    
    def __del__(self):
        self.wait()

    def run(self):
        print 'Setting laser to initial burst parameters for ' + self.dev + ' scan'
        self.laser.StartBurst(self.startParam, self.stopParam, self.stepParam)
        self.burstReady.emit()
        self.quit()
        return   
            
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
            self.msleep(200)
            ps = self.MaxiGauge.pressures()
            MainPress = "{:2.3e} mbar".format(ps[3].pressure)
            SourcePress = "{:2.3e} mbar".format(ps[0].pressure)
            self.pressReadReady.emit([MainPress, SourcePress])
        self.MaxiGauge.disconnect()
        self.quit()
        return

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
        self.setFixedSize(196, 300)
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
            self.setFixedSize(196, 300)

class StartMCPThread(QtCore.QThread):
    def __init__(self, setPotBool, analogIO, stepTime, finalMCP, finalPhos, rampTime, startMCP, startPhos):
        QtCore.QThread.__init__(self)
        self.setPotBool = setPotBool
        self.analogIO = analogIO
        self.stepTime = stepTime*1E-3
        self.startMCP = startMCP
        self.startPhos = startPhos
        self.finalMCP = finalMCP
        self.finalPhos = finalPhos
   
    valueSet = QtCore.pyqtSignal(object)
    settingComplete = QtCore.pyqtSignal()
    
    # override
    def __del__(self):
        self.wait()

    def run(self):
        if self.stepTime >= 0.1 and self.finalMCP > 0:
            ratio = self.finalPhos/float(self.finalMCP)
            i = self.startMCP
            j = self.startPhos
            while self.setPotBool:
                self.analogIO.writeAOMCP(i)
                self.analogIO.writeAOPhos(round(j))
                if i == self.finalMCP:
                    # step up to final setting if ratio deviations
                    j = self.finalPhos
                    self.analogIO.writeAOPhos(j)
                    self.settingComplete.emit()
                    break
                else:
                    i += 1
                    j += ratio
                self.valueSet.emit([i,int(j),0])
                time.sleep(self.stepTime)
            self.quit()
            return
        elif self.finalMCP == 0 and self.finalPhos == 0:
            ratio = self.startPhos/float(self.startMCP)
            i = self.startMCP
            j = self.startPhos
            while self.setPotBool:
                self.analogIO.writeAOMCP(i)
                self.analogIO.writeAOPhos(round(j))
                if i == self.finalMCP:
                    # step up to final setting if ratio deviations
                    self.analogIO.writeAOPhos(0)
                    self.settingComplete.emit()
                    break
                else:
                    i -= 1
                    j -= ratio
                self.valueSet.emit([i,int(j),self.startMCP])
                time.sleep(0.05)
            self.quit()
            return
        else:
            return
      
class StartMCPWin(QtGui.QWidget, ui_form_startmcp):
    def __init__(self, analogIO, MCPVolt, PhosVolt):
        QtGui.QWidget.__init__(self)
        self.setupUi(self)
        self.setWindowTitle('Start MCP/Phos Screen Control')
        self.setFixedSize(363, 303)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.centerWindow()
        self.setPotBool = False
        self.analogIO = analogIO
        self.progBar = self.progressBarMCP
        self.btn_startMCPRamp.clicked.connect(self.setPotentials)
        self.inp_timeStep.setValue(1000)
        self.inp_finalPhos.setValue(3000)
        self.inp_finalMCP.setValue(1200)
        self.out_setMCP.setText(str(MCPVolt))
        self.out_setPhos.setText(str(PhosVolt))
        
        self.inp_finalMCP.editingFinished.connect(self.calcCycleTime)
        self.inp_timeStep.editingFinished.connect(self.calcCycleTime)
        self.calcCycleTime()
         
    winClose = QtCore.pyqtSignal()
    setTextFinal = QtCore.pyqtSignal(object)
    
    def setTextOut(self, text):
        self.out_setMCP.setText(str(text[0]))
        self.out_setPhos.setText(str(text[1]))
        if self.inp_finalMCP.value() != 0:
            self.progBar.setValue((float(text[0])/self.inp_finalMCP.value())*1E2)
        else:
            self.progBar.setValue((float(text[0])/text[2])*1E2)
            
    def calcCycleTime(self):
        self.rampTime = self.inp_finalMCP.value()*self.inp_timeStep.value()*1E-3
        m, s = divmod(int(self.rampTime), 60)
        self.out_cycleTime.setText('{:02d}:{:02d}'.format(m, s))
        if self.inp_timeStep.value() < 100:
                self.inp_timeStep.blockSignals(True)
                reply = QtGui.QMessageBox.warning(self, 'Warning',
                'Time step value too small', QtGui.QMessageBox.Ok)
                self.inp_timeStep.setValue(100)
                self.inp_timeStep.blockSignals(False)
        if self.inp_finalMCP.value() == 0 or self.inp_finalPhos.value() == 0:
            self.inp_finalMCP.setValue(0)
            self.inp_finalPhos.setValue(0)
    
    def setPotentials(self):
        if not(self.setPotBool):
            self.setPotBool = True
            self.btn_startMCPRamp.setText('Pause Ramping')
            self.ctlActive(False)
            self.StartMCPThread = StartMCPThread(True, self.analogIO, self.inp_timeStep.value(),
                                             self.inp_finalMCP.value(), self.inp_finalPhos.value(), self.rampTime,
                                             int(self.out_setMCP.toPlainText()), int(self.out_setPhos.toPlainText()))
            self.StartMCPThread.valueSet.connect(self.setTextOut)
            self.StartMCPThread.settingComplete.connect(self.settingComplete)
            self.StartMCPThread.start()      
        else:
            self.btn_startMCPRamp.setText('Start Ramping')
            self.setPotBool = False
            self.StartMCPThread.setPotBool = False
            
    def ctlActive(self, stateBool):
        self.inp_finalMCP.setEnabled(stateBool)
        self.inp_finalPhos.setEnabled(stateBool)
        self.inp_timeStep.setEnabled(stateBool)
        
    def centerWindow(self):
        frm = self.frameGeometry()
        win = QtGui.QDesktopWidget().availableGeometry().center()
        frm.moveCenter(win)
        self.move(frm.topLeft())
        
    def settingComplete(self):
       self.setPotBool = False
       self.close()
           
    def closeEvent(self, event):
        if self.setPotBool:
            reply = QtGui.QMessageBox.question(self, 'MCP Control Warning',
            "Abort Potential Ramp?", QtGui.QMessageBox.Yes | 
            QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)
            if reply == QtGui.QMessageBox.Yes:
                event.accept()
                self.StartMCPThread.setPotBool = False
                self.btn_startMCPRamp.setText('Start Ramping')
                self.setPotBool = False
                self.winClose.emit()
                self.setTextFinal.emit([self.out_setMCP.toPlainText(), self.out_setPhos.toPlainText()])
            else:
                event.ignore()
        else:
            event.accept()
            self.winClose.emit()
            self.setTextFinal.emit([self.out_setMCP.toPlainText(), self.out_setPhos.toPlainText()])

            
if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    myapp = RSDControl()
    app.exec_()
