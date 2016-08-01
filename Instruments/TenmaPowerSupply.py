# Controller for TENMA  power supply to activate fan
# voltage/current values tested before and channel switched on/off

import serial
import time
 
class TenmaPowerSupplyController(object):
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        self.dev = serial.Serial()
        self.dev.port = 'COM13'
        self.dev.baudrate = 9600
        self.dev.timeout = 1
        self.dev.parity = serial.PARITY_NONE
        self.dev.stopbits = serial.STOPBITS_ONE
        self.dev.bytesize = serial.EIGHTBITS
        self.dev.xonxoff = False
        self.dev.rtscts = False
        self.dev.dsrdtr = False
        self.dev.open()
        self.dev.write('BEEP1')
        self.dev.write('*IDN?')
        serialno = self.dev.read(16)
        print 'Connected to Tenma Power Supply'
        
    def fancontrol(self, bool):
        if bool: self.enableOutput()
        else: self.disableOutput()
        
    def enableOutput(self):
        self.dev.write('OUT1')
        self.dev.read(16)
    
    def disableOutput(self):
        self.dev.write('OUT0')
        self.dev.read(16)
            
    def setVoltOut(self, valin):
        val = "{:05.2f}".format(valin)
        self.dev.write('VSET1:' + val)
        self.dev.read(16)
        
    def setCurrOut(self, valin):
        val = "{:5.3f}".format(valin)
        self.dev.write('ISET1:' + val)
        self.dev.read(16)
        
    def closeDevice(self):
        self.dev.close()
     
if __name__ == '__main__':
    ps = TenmaPowerSupplyController()
    # Stanford PS draw ~0.01-0.03mA, Tenma PS resolution 1mA (10mV)
    ps.setCurrOut(0.1)
    ps.setCurrOut(2)
    ps.setVoltOut(5)
    ps.setVoltOut(12.23)
    ps.setVoltOut(10.5)
    ps.setVoltOut(21.24)
    ps.setVoltOut(31.00)
    ps.dev.write('VSET1?')
    print ps.dev.read(16)
    ps.dev.write('ISET1?')
    print ps.dev.read(16)
    # reset to fan settings
    ps.setCurrOut(2.21)
    ps.setVoltOut(24)
    ps.closeDevice()