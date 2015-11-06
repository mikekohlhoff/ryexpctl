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
        self.dev.open()
        self.dev.write('*IDN?')
        serialno = self.dev.read(16)
        print 'Connected to Power Supply: ' + serialno
        #self.dev.write('RCL1')
        
    def fancontrol(self, bool):
        if bool: self.enableFan()
        else: self.disableFan()
        
    def enableFan(self):
        self.dev.write('OUT1')
    
    def disableFan(self):
        self.dev.write('OUT0')
            
    def closeDevice(self):
        self.dev.close()
     
if __name__ == '__main__':
    ps = TenmaPowerSupplyController()
    ps.enableFan()
    time.sleep(2)
    ps.disableFan()
    ps.closeDevice()