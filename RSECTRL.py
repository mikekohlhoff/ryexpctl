# -*- coding: utf-8 -*-
'''
Control RSE experiment, scope read-out in separate thread that emits data to widget
that handles data evaluation, display and saving
RSDControl was intended to run the surface experiment in combination with a PCB decelerator,
the UCL branch removes these capibilities
'''

import time
from datetime import datetime
import os
import sys
import pickle
import math
import collections
import random
import numpy as np

# UI related
from PyQt4 import QtCore, QtGui, uic
ui_form = uic.loadUiType("rsegui.ui")[0]
ui_form_startmcp = uic.loadUiType("rseguiStartMCP.ui")[0]

# hardware controller modules
from Instruments.LeCroyScopeController import LeCroyScopeControllerVISA
from Instruments.DCONUSB87P4 import USB87P4Controller
from Instruments.PfeifferMaxiGauge import MaxiGauge
from Instruments.QuantumComposerPulseGenerator import PulseGeneratorController
from Instruments.LabJackU3HV import LabJackU3LJTick
from Instruments.PIDController import PIDControl
from Instruments.Agilent33510B import WaveformGeneratorController
from Instruments.WavemeterRead import WavemeterReadController
from Instruments.NIUSB6212 import AnalogOutController

class RSEControl(QtGui.QMainWindow, ui_form):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.initHardware()
        # monitor constants, hasattr(thread) only works before first creation
        self.scopeMon = False
        self.scanMode = False
        self.setPotBool = False
        # if program crashes, reset MCP/Phos analog output
        self.shutdownStatus = [False, 0, 0]
        self.initUI()

    def initUI(self):
        # signals and slots
        self.inp_avgSweeps.editingFinished.connect(self.inp_avgSweeps_changed)
        self.btn_startDataAcq.clicked.connect(self.btn_startDataAcq_clicked)
        self.chk_readScope.clicked.connect(self.chk_readScope_clicked)
        self.inp_gate1Start.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate1Stop.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate2Start.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_gate2Stop.valueChanged.connect(self.setCursorsScopeWidget)
        self.inp_extractDelay.valueChanged.connect(self.setExtractionDelay)
        self.btn_startMCP.clicked.connect(self.startMCPPhos)
        self.inp_voltMCP.valueChanged.connect(self.saveMCPVoltage)
        self.inp_voltPhos.valueChanged.connect(self.saveMCPVoltage)
        self.inp_voltExtract.valueChanged.connect(lambda: self.analogIO.writeAOExtraction(self.inp_voltExtract.value()))
        self.inp_voltOptic1.valueChanged.connect(lambda: self.analogIO.writeAOIonOptic1(self.inp_voltOptic1.value()))
        self.inp_voltMCP.valueChanged.connect(lambda: self.analogIO.writeAOMCP(self.inp_voltMCP.value()))
        self.inp_voltPhos.valueChanged.connect(lambda: self.analogIO.writeAOPhos(self.inp_voltPhos.value()))

        self.chk_PulseValve.stateChanged.connect(self.pulseValveClicked)
        self.chk_ExtractionPulse.stateChanged.connect(lambda: self.pulseGen.switchChl(2, self.chk_ExtractionPulse.isChecked()))
        self.scanModeSelect.currentIndexChanged.connect(lambda: self.tabWidget_ScanParam.setCurrentIndex(self.scanModeSelect.currentIndex()))
        self.tabWidget_ScanParam.currentChanged.connect(lambda: self.scanModeSelect.setCurrentIndex(self.tabWidget_ScanParam.currentIndex()))


        self.chk_sourceControl.clicked.connect(self.switchPressThread)
        self.sliderSource.sliderMoved.connect(self.setSliderVoltOut)
        self.inp_voltSurf.valueChanged.connect(self.setSurfaceBias)
        self.chk_SurfaceBias.clicked.connect(lambda: self.wfGen.switchOutput(1, self.chk_SurfaceBias.isChecked()))
        self.chk_connectWavemeter.clicked.connect(self.switchWavemeterThread)

        # defaults
        self.saveFilePath = 'C:\\Users\\rse\\Documents\\Documents\\Data UCL\\raw data\\2017'
        self.inp_avgSweeps.setValue(10)
        self.cursorPos = np.array([0,0,0,0])
        # have only scope non-scan related controls activated
        self.enableControlsScan(True)
        self.groupBox_DataAcq.setEnabled(False)
        self.tabWidget_ScanParam.setEnabled(False)
        self.groupBox_TOF.setEnabled(False)
        self.out_readSourceGauge.setText('Read out not active')
        currentIndex=self.tabWidget_ScanParam.currentIndex()
        currentWidget=self.tabWidget_ScanParam.currentWidget()
        self.tabWidget_ScanParam.setCurrentIndex(self.scanModeSelect.currentIndex())

        self.LabJack.setLJTick(0, 'A')
        #extraction delay
        self.pulseGen.setDelay(2, float(('{:1.11f}').format(300*1E-6)))
        self.inp_extractDelay.setValue(300)

        # set size of window
        self.setWindowTitle('RSE CONTROL')
        self.centerWindow()
        self.setFixedSize(1062, 688)
        self.setSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        self.show()

    def setExtractionDelay(self):
        if self.inp_extractDelay.hasFocus():
            val = self.inp_extractDelay.value()*1E-6
            self.pulseGen.setDelay(2, float(('{:1.11f}').format(val)))

    def pulseValveClicked(self):
        self.pulseGen.switchChl(1, self.chk_PulseValve.isChecked())

    def setSurfaceBias(self):
        print "TODO"

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
            self.scope.invertTrace(False)
            self.scope.closeConnection()
            self.dataBuf1 = []
            self.dataBuf2 = []
            self.scopeThread = scopeThread(True, True, self.inp_avgSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority)
            self.enableControlsScope(True)
            self.ScopeDisplay.lr1.setMovable(True)
            self.ScopeDisplay.lr2.setMovable(True)
            self.inp_extractDelay.setValue(float(self.pulseGen.readDelay(6))*1E6)
            print "Scope offset to trigger: " + str(self.scopeThread.scope.trigOffsetC1)
        else:
            file = open('lastGateTimes.pckl', 'w')
            pickle.dump([self.inp_gate1Start.value(), self.inp_gate1Stop.value(), \
            self.inp_gate2Start.value(), self.inp_gate2Stop.value()], file)
            file.close()
            self.scopeThread.scopeRead = False
            self.enableControlsScope(False)
            self.scope = LeCroyScopeControllerVISA()
            self.scope.setSweeps(self.inp_avgSweeps.value())
            self.ScopeDisplay.lr1.setMovable(False)
            self.ScopeDisplay.lr2.setMovable(False)
            self.scope.dispOn()
            self.scope.invertTrace(True)

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
            if self.inp_avgSweeps.value() < 2:
                QtGui.QMessageBox.critical(self, 'Data Acquistion Warning', "Average should be at least 2.", QtGui.QMessageBox.Ok)
                return
            if not(self.chk_sourceControl.isChecked()):
                QtGui.QMessageBox.critical(self, 'Data Acquistion Warning', "Activate pulse valve PID control.", QtGui.QMessageBox.Ok)
                return

            self.btn_startDataAcq.setText('Abort Data Acq')
            # reconnect to scope to switch display otherwise access problems
            self.scopeThread.scopeRead = False
            time.sleep(0.4)
            # set scan parameters
            self.enableControlsScan(False)
            #self.line1Pos = self.ScopeDisplay.line1.value()
            self.setScanParams()
            self.scopeThread = scopeThread(True, True, self.inp_avgSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            # set scan flag in thread
            if not('Wavelength' in self.scanParam):
                self.resetDatBuf()
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority)
        else:
            # abort scan
            if 'Wavelength' in self.scanParam:
                self.devParam.CancelBurst()
            self.scopeThread.scopeRead = False
            print 'DATA ACQ OFF'
            # reset devices to value before scan
            self.setParam = self.beforescanParam
            self.scanSetDevice()
            if len(self.DataDisplay.dataTrace1) > 0:
                self.openSaveFile()
            else:
                time.sleep(.4)
            self.scopeThread = scopeThread(True, True, self.inp_avgSweeps.value())
            self.scopeThread.dataReady.connect(self.dataAcquisition)
            self.scopeThread.start(priority=QtCore.QThread.HighestPriority)
            self.btn_startDataAcq.setText('Start Data Acq')
            self.progressBarScan.setValue(0)
            self.enableControlsScan(True)
            self.inp_fileComment.setText('')
            self.inp_fileName.setText('')

    def setScanParams(self):
        self.scanParam = str(self.scanModeSelect.currentText())
        if self.scanParam == 'Voltage':
            self.scanParam = self.scanParam + ' ' + str(self.voltageSelectScan.currentText())
            self.startParam = self.inp_startField.value()
            self.stopParam = self.inp_stopField.value()
            self.stepParam = self.inp_incrField.value()
            self.setParam = self.startParam
            self.setOutParam = self.out_voltMon
            if 'Extraction' in self.scanParam:
                self.devParam = 'Extraction'
                self.beforescanParam = self.inp_voltExtract.value()
            elif 'Ion' in self.scanParam:
                self.devParam = 'Ion1'
                self.beforescanParam = self.inp_voltOptic1.value()
            if self.stopParam > self.startParam:
                self.scanDirection = 1
            else:
                self.scanDirection = -1
            self.scanSetDevice()
            self.deviceRelax(0.8)
        elif self.scanParam == 'Wavelength':
            self.scanParam = self.scanParam + ' ' + str(self.laserSelectScan.currentText())
            self.startParam = self.inp_startWLVolt.value()
            self.stopParam = self.inp_stopWLVolt.value()
            self.stepParam = self.inp_incrWLVolt.value()
            self.setParam = self.startParam
            self.setOutParam = self.out_WLMon
            if 'IR' in self.scanParam:
                self.beforescanParam = self.inp_setWL_VUV.value()
                # TODO
                self.devParam = self.VUVLaser
            else:
                self.beforescanParam = self.inp_setWL_UV.value()
                self.devParam = self.UVLaser
            self.setOutParam.setText(str(self.beforescanParam))

            if self.stopParam > self.startParam:
                self.scanDirection = 1
            else:
                self.scanDirection = -1
            self.burstStart.start()
        elif 'Delay' in self.scanParam:
            self.scanParam = self.scanParam + ' ' + str(self.delaySelectScan.currentText())
            self.startParam = self.inp_startDelay.value()*1E-6
            self.stopParam = self.inp_stopDelay.value()*1E-6
            self.stepParam = self.inp_incrDelay.value()*1E-6
            self.setParam = self.startParam
            self.setOutParam = self.out_delayMon
            # set delay generator channel for scan
            if 'Extract' in self.scanParam:
                # Fire channel
                self.devParam = 2

            self.beforescanParam = float(self.pulseGen.readDelay(self.devParam))
            if self.stopParam > self.startParam:
                self.scanDirection = 1
            else:
                self.scanDirection = -1
            self.scanSetDevice()
            self.deviceRelax(0.8)

        elif 'Detection' in self.scanParam:
            self.startParam = [self.inp_startFieldDet.value(), self.inp_startIonDet.value()]
            self.stopParam = [self.inp_stopFieldDet.value(), self.inp_stopIonDet.value()]
            self.stepParam = [self.inp_incrFieldDet.value(), self.inp_incrIonDet.value()]
            self.setParam = [self.startParam[0], self.startParam[1]]
            self.setOutParam = [self.out_voltMonDet1, self.out_voltMonDet2]
            self.beforescanParam = [self.inp_voltExtract.value(), self.inp_voltOptic1.value()]
            self.scanDirection = [0, 0]
            if self.stopParam[0] > self.startParam[0]: self.scanDirection[0] = 1
            else: self.scanDirection[0] = -1
            if self.stopParam[1] > self.startParam[1]: self.scanDirection[1] = 1
            else: self.scanDirection[1] = -1
            self.numpoints = int((1+abs(float(self.stopParam[0]-self.startParam[0]))/self.stepParam[0])*(1+abs(self.stopParam[1]-self.startParam[1])/self.stepParam[1]))
            self.datalen = int(1+abs(float(self.stopParam[0]-self.startParam[0]))/self.stepParam[0])
            self.countpoints = 0
            self.scanSetDevice()
            self.deviceRelax(0.8)

    def dataAcquisition(self, data):
        # add data, substract baseline per trace
        if self.chk_baselinecorrect.isChecked():
            data1 = data[0] - np.mean(data[0][-3000:-1000])
            data2 = data[1] - np.mean(data[1][-3000:-1000])
        else:
            data1 = data[0] - np.mean(data[0][0:100])
            data2 = data[1] - np.mean(data[1][0:100])
        self.dataBuf1.append(data1)
        self.dataBuf2.append(data2)
        self.cursorPos = self.ScopeDisplay.getCursors()
        self.setGateField(self.cursorPos)
        if len(self.dataBuf1) >= self.scopeThread.avgSweeps:
            # deque trace buffer when average shots is reached
            dataIn1 = self.dataBuf1[0:self.scopeThread.avgSweeps]
            dataIn2 = self.dataBuf2[0:self.scopeThread.avgSweeps]
            del self.dataBuf1[0:self.scopeThread.avgSweeps]
            del self.dataBuf2[0:self.scopeThread.avgSweeps]
            if self.scopeMon and not(self.scanMode):
                # scope monitor plotting
                self.ScopeDisplay.plotMon(dataIn1, dataIn2, self.scopeThread.scope.timeincrC1, self.scopeThread.scope.timeincrC2)
            elif self.scopeMon and self.scanMode:
                # scan plotting
                self.ScopeDisplay.plotDataAcq(dataIn1, dataIn2, self.cursorPos, self.scopeThread.scope.timeincrC1, \
                                              self.scopeThread.scope.timeincrC2)
                if ('Velocity' in self.scanParam) or ('Detection' in self.scanParam):
                    # assume matrix scans in order for i in delayvals: for j in voltvals = signal[i][j]
                    # param[0]=voltage, param[1]=delay
                    self.countpoints += 1
                    self.DataDisplay.plotMatrix(dataIn1, dataIn2, self.setParam, self.cursorPos, self.scanParam, self.scopeThread.scope.timeincrC1, \
                                                self.scopeThread.scope.timeincrC2, self.datalen, self.countpoints, self.numpoints, self.scanParam)
                    if (abs(self.setParam[0] - self.stopParam[0]) == 0) and (abs(self.setParam[1] - self.stopParam[1]) < 25E-11):
                        # send signal to abort measurement
                        self.progressBarScan.setValue((float(self.countpoints)/self.numpoints)*1E2)
                        self.btn_startDataAcq_clicked()
                    elif (abs(self.setParam[0] - self.stopParam[0]) == 0) and not(abs(self.setParam[1] - self.stopParam[1]) < 25E-11):
                        # step delay/optic when voltage trace finished
                        self.setParam[0] = self.startParam[0]
                        self.setParam[1] += self.scanDirection[1]*self.stepParam[1]
                        self.scanSetDevice()
                        self.deviceRelax(0.8)
                        self.progressBarScan.setValue((float(self.countpoints)/self.numpoints)*1E2)
                    elif (not(abs(self.setParam[0] - self.stopParam[0]) == 0) and not(abs(self.setParam[1] - self.stopParam[1]) < 25E-11)) or \
                         (not(abs(self.setParam[0] - self.stopParam[0]) == 0) and (abs(self.setParam[1] - self.stopParam[1]) < 25E-11)):
                        # step voltage, second or case account for last iteration of delay
                        self.setParam[0] += self.scanDirection[0]*self.stepParam[0]
                        self.scanSetDevice()
                        self.progressBarScan.setValue((float(self.countpoints)/self.numpoints)*1E2)
                else:
                    self.DataDisplay.plot(dataIn1, dataIn2, self.setParam, self.cursorPos, self.scanParam, \
                                          self.scopeThread.scope.timeincrC1, self.scopeThread.scope.timeincrC2)
                    # eps for floating point comparison in delay scans, 25ps max resolution for delay generator
                    if abs(self.setParam - self.stopParam) < 25E-11:
                        # last data point recorded, save data, reset to value before scan in btn_acq_clicked()
                        self.progressBarScan.setValue((float(abs(self.setParam - self.startParam))/abs(self.stopParam - self.startParam))*1E2)
                        self.btn_startDataAcq_clicked()
                    else:
                        # step scan parameter
                        if not('Wavelength' in self.scanParam):
                            self.setParam += self.scanDirection*self.stepParam
                        self.scanSetDevice()
                        self.progressBarScan.setValue((float(abs(self.setParam - self.startParam))/abs(self.stopParam - self.startParam))*1E2)

    def deviceRelax(self, sleeptime):
        # allow for e.g. power supplies to settle potentials
        self.scopeThread.blockSignals(True)
        time.sleep(sleeptime)
        self.dataBuf1 = []
        self.dataBuf2 = []
        self.scopeThread.blockSignals(False)

    def scanSetDevice(self):
        if 'Voltage' in self.scanParam:
            if self.devParam == 'Extraction':
                self.analogIO.writeAOExtraction(self.setParam)
            elif self.devParam == 'Ion1':
                self.analogIO.writeAOIonOptic1(self.setParam)
            outVal = self.setParam
            self.setOutParam.setText(str(outVal))
        elif 'Wavelength' in self.scanParam:
            # reset laser to former wavelength
            if not self.scanMode and 'UV' in self.scanParam:
                self.setLaser = LaserThread(self.devParam, self.setParam, self.inp_setWL_UV)
                self.setLaser.start()
                self.out_WLMon.setText('{:3.4f}'.format(self.setParam))
                return
            elif not self.scanMode and 'IR' in self.scanParam:
                self.setLaser = LaserThread(self.devParam, self.setParam, self.inp_setWL_VUV)
                self.setLaser.start()
                self.out_WLMon.setText('{:3.4f}'.format(self.setParam))
                return
            (wl, cont) = self.devParam.NextBurst()
            self.setParam = float('{:.5f}'.format(wl))
            outVal = '{:3.4f}'.format(wl)
            # if sum(WLsteps) != abs(WLstop - WLstart)
            if not cont: self.setParam = self.stopParam
            self.setOutParam.setText(str(outVal))
        elif 'Delay' in self.scanParam:
             self.pulseGen.setDelay(self.devParam, float('{:1.11f}'.format(self.setParam)))
             outVal = '{:4.5f}'.format(self.setParam*1E6)
             self.setOutParam.setText(str(outVal))
        elif 'Velocity' in self.scanParam:
            self.analogIO.writeAOExtraction(self.setParam[0])
            self.pulseGen.setDelay(self.devParam, float('{:1.11f}'.format(self.setParam[1])))
            outVal = [self.setParam[0], '{:4.5f}'.format(self.setParam[1]*1E6)]
            self.setOutParam[0].setText(str(outVal[0]))
            self.setOutParam[1].setText(str(outVal[1]))
        elif 'Detection' in self.scanParam:
            self.analogIO.writeAOExtraction(self.setParam[0])
            self.analogIO.writeAOIonOptic1(self.setParam[1])
            outVal = [self.setParam[0], self.setParam[1]]
            self.setOutParam[0].setText(str(outVal[0]))
            self.setOutParam[1].setText(str(outVal[1]))

    def resetDatBuf(self):
        #reset recorded data
        self.scanMode = True
        print 'DATA ACQ ON'
        self.dataBuf1 = []
        self.dataBuf2 = []
        self.DataDisplay.dataTrace1 = []
        self.DataDisplay.dataTrace2 = []
        self.DataDisplay.errTrace1 = []
        self.DataDisplay.errTrace2 = []
        self.DataDisplay.paramTrace = []
        self.dataTracePrev1 = []
        self.dataTracePrev2 = []

    def openSaveFile(self):
        fileName = self.scanParam + ' Scan ' + '{:s}'.format(self.inp_fileName.text()) + time.strftime("%y%m%d") + time.strftime("%H%M")
        filePath = os.path.join(self.saveFilePath, fileName)
        savePath = QtGui.QFileDialog.getSaveFileName(self, 'Save Traces', filePath, '(*.txt)')
        if not(str(savePath)): return
        if ('Velocity' in self.scanParam) or ('Detection' in self.scanParam):

            #voltage = np.asarray(self.DataDisplay.paramTrace)[:,0]
            #delay = np.asarray(self.DataDisplay.paramTrace)[:,1]
            #saveData = np.hstack((np.vstack(voltage), np.vstack(delay), np.vstack(np.asarray(self.DataDisplay.dataTrace1)),
            #                    np.vstack(np.asarray(self.DataDisplay.errTrace1)), np.vstack(np.asarray(self.DataDisplay.dataTrace2)),
            #                    np.vstack(np.asarray(self.DataDisplay.errTrace2))))
            f = open('tempdata.txt', 'r')
            saveData = f.read()
            f.close()
            os.remove('tempdata.txt')
            if 'Velocity' in self.scanParam:
                dataStructure = 'Data structure: Voltage x Delay, ' + '{:.0f}'.format(1+(abs(float(self.stopParam[0]-self.startParam[0]))/self.stepParam[0])) + \
                                'x' + '{:.0f}'.format(1+(abs(self.stopParam[1]-self.startParam[1])/self.stepParam[1]))
                header= u'VoltageExtraction\tDelayRydExc\tDat1\tErr1\tDat2\tErr2'
            elif 'Detection' in self.scanParam:
                dataStructure = 'Data structure: Voltage Extraction x Voltage Ion Optic 1, ' + '{:.0f}'.format(1+(abs(float(self.stopParam[0]-self.startParam[0]))/self.stepParam[0])) + \
                                'x' + '{:.0f}'.format(1+(abs(self.stopParam[1]-self.startParam[1])/self.stepParam[1]))
                header= u'VoltageExtraction\tVoltageIonO1\tDat1\tErr1\tDat2\tErr2'
            f = open(str(savePath), 'w')
            f.write('# Comment: ' + str(self.inp_fileComment.text()) + '\n')
            f.write(dataStructure + '\n')
            f.write(header + '\n')
            f.write(saveData)
            f.close()
        else:
            saveData = np.hstack((np.vstack(np.asarray(self.DataDisplay.paramTrace)), np.vstack(np.asarray(self.DataDisplay.dataTrace1)),
                                np.vstack(np.asarray(self.DataDisplay.errTrace1)), np.vstack(np.asarray(self.DataDisplay.dataTrace2)),
                                np.vstack(np.asarray(self.DataDisplay.errTrace2))))
            print 'Save data file'
            if 'Voltage' in self.scanParam:
                fmtIn = ['%i' , '%.3f', '%.3f', '%.3f', '%.3f']
            elif 'Wavelength' in self.scanParam:
                # smallest step .00025nm
                fmtIn = ['%.5f' , '%.3f', '%.3f', '%.3f', '%.3f']
            elif 'Delay' in self.scanParam:
                fmtIn = ['%.11f' , '%.3f', '%.3f', '%.3f', '%.3f']
            np.savetxt(str(savePath), saveData, fmt=fmtIn, delimiter='\t', newline='\n', header=self.scanParam+(u'\tDat1\tErr1\tDat2\tErr2'),
                      footer='', comments=('# Comment: ' + str(self.inp_fileComment.text()) + '\n'))
        self.saveFilePath = os.path.dirname(str(savePath))

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
        self.groupBox_Laser.setEnabled(boolEnbl)
        self.groupBox_MCP.setEnabled(boolEnbl)
        self.groupBox_Extraction.setEnabled(boolEnbl)
        self.groupBox_Scope.setEnabled(boolEnbl)
        self.groupBox_DevControl.setEnabled(boolEnbl)
        self.groupBox_TOF.setEnabled(boolEnbl)
        self.groupBox_Decelerator.setEnabled(boolEnbl)
        self.scanModeSelect.setEnabled(boolEnbl)
        self.inp_fileName.setEnabled(boolEnbl)

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
                self.dataBuf1 = []
                self.dataBuf2 = []

    def switchWavemeterThread(self):
        """Enable/disable wavemeter readout"""
        if self.chk_connectWavemeter.isChecked():
            self.wvm = WavemeterReadController()
            self.WavemeterThread = WavemeterThread(self.wvm)
            self.WavemeterThread.wlReadReady.connect(self.setWavemeterRead)
            self.WavemeterThread.start()
        else:
            self.WavemeterThread.ReadActive = False

    def setWavemeterRead(self, wlRead):
        '''Update front panel'''
        self.out_wlUV.setText(wlRead[0])
        self.out_wlIR.setText(wlRead[1])

    def startPressThread(self):
        '''create maxi gauge thread and _run() without pid feedback loop'''
        if self.chk_readMainGauge.isChecked():
            mainstate = 'ON'
        else:
            mainstate = 'OFF'
        self.PressureThread = PressureThread(True, mainstate, self.chk_readMainGauge, self.MaxiGauge)
        self.PressureThread.pressReadReady.connect(self.setPressRead)
        self.PressureThread.start()
        self.pressThread = True
        self.inp_sourceChamber.setEnabled(False)
        self.chk_readMainGauge.setEnabled(True)
        self.sliderSource.setEnabled(True)

    def startPressThreadData(self):
        self.PressureThreadData = PressureThreadData(True, self.LabJack, self.MaxiGauge, self.inp_sourceChamber)
        self.PressureThreadData.pressReadReady.connect(self.setPressRead)
        self.PressureThreadData.start()
        self.pressThread = False
        self.inp_sourceChamber.setEnabled(True)
        self.chk_readMainGauge.setEnabled(False)
        self.chk_readMainGauge.setCheckState(QtCore.Qt.Unchecked)
        self.sliderSource.setEnabled(False)

    def switchPressThread(self):
        if self.pressThread:
            if not(self.chk_PulseValve.isChecked()):
                QtGui.QMessageBox.critical(self, 'PID Controller Warning', "Pulse valve trigger not enabled.", QtGui.QMessageBox.Ok)
                self.inp_sourceChamber.blockSignals(True)
                self.chk_sourceControl.setCheckState(QtCore.Qt.Unchecked)
                self.inp_sourceChamber.blockSignals(False)
                return
            self.PressureThread.blockSignals(True)
            self.PressureThread.ReadActive = False
            time.sleep(0.6)
            self.PressureThread.blockSignals(False)
            self.startPressThreadData()
        else:
            self.PressureThreadData.ReadActive = False
            time.sleep(0.2)
            # reset to pressure before PID activated
            val = float(self.sliderSource.value())/100
            self.LabJack.setLJTick(val, 'A')
            self.startPressThread()

    def setPressRead(self, pressRead):
        self.out_readMainGauge.setText(pressRead[1])
        if not(self.pressThread):
            if self.PressureThreadData.dispincr%18==0:
                self.out_readSourceGauge.setText(pressRead[0])
                self.out_piderr.setText('{:3.1f}'.format((abs(pressRead[3])/self.inp_sourceChamber.value())*100))
        else:
            self.out_readSourceGauge.setText(pressRead[0])
            if self.chk_PulseValve.isChecked():
                self.out_piderr.setText('off')

    def setSliderVoltOut(self):
        sender = self.sender()
        val = float(sender.value())/100
        self.LabJack.setLJTick(val, 'A')

    def closeEvent(self, event):
        if hasattr(self, 'scopeThread'):
            self.scopeThread.blockSignals(True)
        if not(self.setPotBool):
            reply = QtGui.QMessageBox.question(self, 'RSE Control',
                "Shut down experiment control?", QtGui.QMessageBox.Yes |
                QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)
            if reply == QtGui.QMessageBox.Yes:
                event.accept()
                self.shutDownExperiment()
            else:
                event.ignore()
                if hasattr(self, 'scopeThread'):
                    self.scopeThread.blockSignals(False)
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

        # scope init here for calib and WFSU,
        # conncection closed when scope read-out active
        self.scope = LeCroyScopeControllerVISA()
        self.scope.initialize()
        self.scope.invertTrace(True)
        self.MaxiGauge = MaxiGauge('COM8')
        # Chl A: PID controller
        self.LabJack = LabJackU3LJTick()
        self.wfGen = WaveformGeneratorController()
        self.NIAO = AnalogOutController()
        self.startPressThread()
        print '-----------------------------------------------------------------------------'

    def shutDownExperiment(self):
        self.blockSignals(True)
        self.analogIO.writeAOExtraction(0)
        self.analogIO.writeAOIonOptic1(0)
        self.shutdownStatus[0] = True
        self.saveMCPVoltage()
        self.LabJack.setLJTick(0, 'A')
        self.LabJack.setLJTick(0, 'B')
        if hasattr(self, 'scopeThread'):
            self.scopeThread.scopeRead = False
            time.sleep(.2)
            self.scopeThread.terminate()
        if hasattr(self, 'scope'):
            self.scope.closeConnection()
        if hasattr(self, 'PressureThread') and self.pressThread:
            self.PressureThread.ReadActive = False
            time.sleep(0.8)
            self.MaxiGauge.disconnect()
        if hasattr(self, 'PressureThreadData') and not(self.pressThread):
            self.PressureThreadData.ReadActive = False
            time.sleep(0.1)
            self.MaxiGauge.disconnect()
        print 'Releasing controllers:'
        self.analogIO.closeDevice()
        self.LabJack.closeDevice()
        self.wfGen.closeConnection()
        if hasattr(self, 'WavemeterThread'):
            self.WavemeterThread.ReadActive = False
            self.wvm.closeConnection()
        self.NIAO.closeDevice()
        self.pulseGen.closeConnection()

# subclass qthread (not recommended officially, old style)
class scopeThread(QtCore.QThread):
    def __init__(self, scopeRead=True, dispOff=False, avgSweeps=1):
        QtCore.QThread.__init__(self)
        self.scopeRead = scopeRead
        self.scope = LeCroyScopeControllerVISA()
        # averages for data eval with single traces from scope
        self.avgSweeps = avgSweeps
        self.scope.setSweeps(1)
        self.scope.setScales()
        if dispOff:
            self.scope.dispOff()

    dataReady = QtCore.pyqtSignal(object)
    # override
    def __del__(self):
        self.wait()

    def run(self):
        self.scope.clearSweeps()
        while self.scopeRead:
            data = self.scope.armwaitread()
            self.dataReady.emit(data)
        # return control to scope
        self.scope.dispOn()
        self.scope.trigModeNormal()
        self.scope.closeConnection()
        self.quit()
        return

class WavemeterThread(QtCore.QThread):
    "Access wavemeter and read wavelengths"
    def __init__(self, wvm):
        QtCore.QThread.__init__(self)
        self.wvm = wvm
        self.ReadActive = True

    wlReadReady = QtCore.pyqtSignal(object)

    def __del__(self):
        self.wait()

    def run(self):
        while self.ReadActive:
            UV, IR = self.wvm.getWavelength()
            self.wlReadReady.emit([UV, IR])
            self.msleep(200)
        self.quit()
        return

class PressureThread(QtCore.QThread):
    def __init__(self, ReadActive, MainState, refmain, MaxiGauge):
        QtCore.QThread.__init__(self)
        self.ReadActive = ReadActive
        self.refmain = refmain
        self.MaxiGauge = MaxiGauge
        self.MaxiGauge.gaugeSwitch(4, MainState)

    pressReadReady = QtCore.pyqtSignal(object)

    def __del__(self):
        self.wait()

    def run(self):
        '''
        sensor 3 = source, 4 = main chamber
        source not switched since it might not switch back to second stage
        '''
        while self.ReadActive:
            if self.refmain.isChecked():
                state = 'ON'
                ps = self.MaxiGauge.pressureSensor(4)
                MainPress = "{:2.2e} mbar".format(ps.pressure)
            else:
                state = 'OFF'
                MainPress = 'Gauge turned off'
            self.MaxiGauge.gaugeSwitch(4, state)
            ps = self.MaxiGauge.pressureSensor(3)
            SourcePress = "{:2.2e} mbar".format(ps.pressure)
            self.pressReadReady.emit([SourcePress, MainPress, ps.pressure])
            self.msleep(400)
        self.quit()
        return

class PressureThreadData(QtCore.QThread):
    def __init__(self, ReadActive, LabJack, MaxiGauge, refval):
        QtCore.QThread.__init__(self)
        self.ReadActive = ReadActive
        self.labjack = LabJack
        self.mg = MaxiGauge
        self.mg.gaugeSwitch(4, 'OFF')
        # __init__(self, P=2.0, I=0.0, D=1.0, Derivator=0, Integrator=0,
        # Integrator_max=500, Integrator_min=-500):
        self.pid = PIDControl(0.02, 0.02, 0.008, 0, 0, 500, -500)
        self.setpoint = refval
        # input field in E-6
        self.pid.setPoint(self.setpoint.value())
        self.dispincr = 1

    pressReadReady = QtCore.pyqtSignal(object)
    def __del__(self):
        self.wait()

    def run(self):
        while self.ReadActive:
            # check for change in setpoint
            if self.setpoint.value() != self.pid.getPoint():
                self.pid.setPoint(self.setpoint.value())
            # output for front panel
            ps = self.mg.pressureSensor(3)
            SourcePress = "{:2.2e} mbar".format(ps.pressure)
            self.pressReadReady.emit([SourcePress, 'Gauge turned off', ps.pressure, self.pid.getError()])
            mv = self.pid.update(ps.pressure*1E6)
            self.labjack.setLJTick(mv, 'A')
            self.dispincr += 1
        self.quit()
        return

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
                time.sleep(0.06)
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
            self.StartMCPThread.start(priority=QtCore.QThread.HighPriority)
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
    myapp = RSEControl()
    app.exec_()
