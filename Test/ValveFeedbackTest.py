from PfeifferMaxiGauge import MaxiGauge
from LabJackU3HV import LabJackU3LJTick
from PyQt4 import QtCore, QtGui
import time
import sys

class valveFeedback(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.mg = MaxiGauge('COM1')
        self.ljtick = LabJackU3LJTick()
        print self.mg.pressures()
        print self.ljtick.device.serialNumber
        self.setWindowTitle('valve test')
        self.setFixedSize(200, 120)
        self.show()
        time.sleep(4)
        self.startFeedbackThread()
    
    def startFeedbackThread(self):
        '''create maxi gauge thread and _run()'''
        # switch of main chamber, measurement mode presumed, un-check box
        #self.mg.gaugeSwitch(4, 'ON')
        self.PressureThread = PressureReadThread(True, self.mg)
        self.PressureThread.pressReadReady.connect(self.printSourcePressure)
        self.PressureThread.start(priority=QtCore.QThread.HighPriority)
        #self.pressThread = True
        
    def printSourcePressure(self, read):
        print read[0]
        print read[1]
  

class PressureReadThread(QtCore.QThread):
    def __init__(self, fbactive, mg):
        QtCore.QThread.__init__(self)
        self.mg = mg
        
    pressReadReady = QtCore.pyqtSignal(object)
    
    def __del__(self):
        self.wait()
        
    def run(self):
        t1 = time.clock()
        it = 1
        tacc = 0.0
        for j in range(1000):
            self.mg.gaugeSwitch(4, 'ON')
            ps = self.mg.pressureSensor(1)
            SourcePress = "{:2.3e} mbar".format(ps.pressure)
            tacc += time.clock() - t1
            it += 1
            t1 = time.clock()
            self.pressReadReady.emit([SourcePress, tacc*1000/it])
        self.quit()
        return
        
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    vfb = valveFeedback()
    app.exec_()
