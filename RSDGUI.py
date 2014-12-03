import time
from datetime import datetime
import os
import sys

PROJECT_ROOT_DIRECTORY = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0]))))
print PROJECT_ROOT_DIRECTORY

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
from Instruments.LeCroyScopeController import *
from Instruments.WaveformPotentials import WaveformPotentials21Elec
from multiprocessing import Pipe, Process

class RSDControl(QtGui.QMainWindow, ui_form):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.initHardware()
        self.initUI()

    def initUI(self):
        self.inp_aveSweeps.editingFinished.connect(self.inp_aveSweeps_changed)
        self.inp_initVel.editingFinished.connect(self.setPCBPotentials)
        self.inp_finalVel.editingFinished.connect(self.setPCBPotentials)
        self.inp_inTime.editingFinished.connect(self.setPCBPotentials)
        self.inp_outDist.editingFinished.connect(self.setPCBPotentials)
        self.inp_sampleRate.editingFinished.connect(self.reconfigureDIOCard)
        self.btn_wfOutput.clicked.connect(self.btn_wfOutput_clicked)
        self.chk_extTrig.stateChanged.connect(self.chk_extTrig_changed)
        self.btn_wfOutput.setEnabled(True)
        self.btn_startAcq.clicked.connect(self.btn_startAcq_clicked)

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
        inTime = 1
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
        if hasattr(self.wfPotentials, 'plotTime'):
            argX = self.wfPotentials.plotTime
            argY = self.wfPotentials.potentialsOut
            self.WaveformDisplay.canvas.ax.clear()
            self.WaveformDisplay.canvas.ax.plot(argX, argY[0,:], 'b', label="1", linewidth=1.5)
            self.WaveformDisplay.canvas.ax.plot(argX, argY[1,:], 'r', label="2", linewidth=1.5)
            self.WaveformDisplay.canvas.ax.plot(argX, argY[2,:], 'g', label="3", linewidth=1.5)
            self.WaveformDisplay.canvas.ax.plot(argX, argY[3,:], 'b--', label="4", linewidth=1.5)
            self.WaveformDisplay.canvas.ax.plot(argX, argY[4,:], 'r--', label="5", linewidth=1.5)
            self.WaveformDisplay.canvas.ax.plot(argX, argY[5,:], 'g--', label="6", linewidth=1.5)
            self.WaveformDisplay.canvas.ax.axis([-2, self.wfPotentials.plotTime[-1]+0.5, self.wfPotentials.maxAmp*-2-10, self.wfPotentials.maxAmp*2+10])
            self.WaveformDisplay.canvas.ax.grid(True)
            self.WaveformDisplay.canvas.ax.set_title("Calculated PCB potentials")
            self.WaveformDisplay.canvas.ax.set_xlabel("Time ($\mu$s)")
            self.WaveformDisplay.canvas.ax.set_ylabel("Amplitude (bits)")
            self.WaveformDisplay.canvas.ax.legend(loc="lower right")
            # mark different phases in potential generation 
            self.WaveformDisplay.canvas.ax.plot([self.wfPotentials.incplTime,self.wfPotentials.incplTime],[(self.wfPotentials.maxAmp*2+10),\
            (self.wfPotentials.maxAmp*(-2)-10)], 'k--', linewidth=1.5)
            self.WaveformDisplay.canvas.ax.plot([self.wfPotentials.plotTime[-1]-self.wfPotentials.outcplTime,\
            self.wfPotentials.plotTime[-1]-self.wfPotentials.outcplTime], [self.wfPotentials.maxAmp*-2-1,self.wfPotentials.maxAmp*2+1], 'k--', \
            linewidth=1.5)
            #self.WaveformDisplay.canvas.ax.plot([self.wfPotentials.incplTime+self.wfPotentials.decelTime,\
            #self.wfPotentials.incplTime+self.wfPotentials.decelTime],[self.wfPotentials.maxAmp*-2-1, self.wfPotentials.maxAmp*2+1], 'k--', linewidth=1)
            self.WaveformDisplay.canvas.fig.patch.set_alpha(0)
            self.WaveformDisplay.canvas.fig.tight_layout()
            self.WaveformDisplay.canvas.draw()
        else:
            print 'No potentials generated'
           
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
        
    def acquisitionLoop(self):
        # handle acquisition of scope data
        scope.setScales()
        acquire = False
        while True:
            # process incoming messages
            if pipe.poll():
                msg = pipe.recv()
                print 'received message', msg
                if msg[0] == 'QUIT':
                    break
                elif msg[0] == 'ACTIVATE':
                    acquire = msg[1]
                else:
                    print 'UNKNOWN COMMAND received!'
        
        if acquire:
            data = scope.armwaitread()
            pipe.send(data)
        else:
            time.sleep(.1)

    def btn_startAcq_clicked(self):
        # connect to acq loop
        self.btn_startAcq.setEnabled(False)
        # parent connection, child connection
        self.pipe, pipe = Pipe()
        self.acqLoop = Process(target=acquisitionLoop, args=(pipe,))
        self.acqLoop.daemon = True
        self.acqLoop.start()
        print 'Data acquisition started'
        
    def stopAcquisition(self):
        self.pipe.recv()
        self.pipe.close()
        self.acqLoop.join()
        print 'Acquisition stopped'

    def shutDownExperiment(self):
        print 'Release controllers'


if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    
    myapp = RSDControl()
    #myapp.initHardware()

    sys.exit(app.exec_())


