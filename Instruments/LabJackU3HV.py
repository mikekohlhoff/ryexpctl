# Controller for Labjack U3-HV with LJTICKDAC extension

import sys
import struct
# load the labjack driver
try:
    import LabJackPython
    import u3
except:
    print "Driver error"
    sys.exit(1)

def toDouble(buffer):
    """
    Name: toDouble(buffer)
    Args: buffer, an array with 8 bytes
    Desc: Converts the 8 byte array into a floating point number.
    """
    if type(buffer) == type(''):
        bufferStr = buffer[:8]
    else:
        bufferStr = ''.join(chr(x) for x in buffer[:8])
    dec, wh = struct.unpack('<Ii', bufferStr)
    return float(wh) + float(dec)/2**32
    
class LabJackU3LJTick(object):
    """
    LabJack Python modules to set the value of DACA and DACB in a LJ-TickDAC
    """
    
    U3 = 3
    U6 = 6
    UE9 = 9
    AUTO = 0
    AIN_PIN_DEFAULT = -1 # AIN must be configured
    DAC_PIN_DEFAULT = 0
    U3_DAC_PIN_OFFSET = 4
    EEPROM_ADDRESS = 0x50
    DAC_ADDRESS = 0x12
    
    def __init__(self):
        print '-----------------------------------------------------------------------------'    
        # Set defaults
        self.ainPin = LabJackU3LJTick.AIN_PIN_DEFAULT
        self.dacPin = LabJackU3LJTick.DAC_PIN_DEFAULT
        
        self.loadDevice()
        print 'LabJackTick found, Serial Number: ' + str(self.device.serialNumber)
     
    def loadDevice(self):
        try:
            self.searchForDevices()
            # Determine which device to use
            if self.u3Available: self.deviceType = LabJackU3LJTick.U3
            else:
                print "Fatal Error: No LabJacks were found to be connected to your computer"
                sys.exit()
            self.loadU3(self.deviceType)
            
        except:
            print "Fatal Python error:" + str(sys.exc_info()[1])
            sys.exit()
    
    def searchForDevices(self):
        self.u3Available = len(LabJackPython.listAll(LabJackU3LJTick.U3)) > 0
        
    def loadU3(self, deviceType):    
        self.deviceType = deviceType
        self.device = u3.U3()
            
        # Configure pins if U3
        if self.deviceType == LabJackU3LJTick.U3:
            self.device.configIO(FIOAnalog=15, TimerCounterPinOffset=8) # Configures FIO0-2 as analog
        
        # Get the calibration constants
        self.getCalConstants()
    
    def getCalConstants(self):
        sclPin = self.dacPin + LabJackU3LJTick.U3_DAC_PIN_OFFSET
        sdaPin = sclPin + 1

        # Make request
        data = self.device.i2c(LabJackU3LJTick.EEPROM_ADDRESS, [64], NumI2CBytesToReceive=36, SDAPinNum = sdaPin, SCLPinNum = sclPin)
        response = data['I2CBytes']
        self.aSlope = toDouble(response[0:8])
        self.aOffset = toDouble(response[8:16])
        self.bSlope = toDouble(response[16:24])
        self.bOffset = toDouble(response[24:32])

        if 255 in response: print "Make sure the LabJackU3LJTick is properly attached"
    
    def setDevice(self, val, chl):
        """
        Changes DACA and DACB to the amounts specified by the user
        """
        # Determine pin numbers
        sclPin = self.dacPin + LabJackU3LJTick.U3_DAC_PIN_OFFSET
        sdaPin = sclPin + 1

        # Make requests
        if chl == 'A':
            # PID output range
            if val > 10: val = 10
            if val < 0: val = 0
            voltageA = float(val)
            try:
                self.device.i2c(LabJackU3LJTick.DAC_ADDRESS, [48, int(((voltageA*self.aSlope)+self.aOffset)/256), int(((voltageA*self.aSlope)+self.aOffset)%256)], SDAPinNum = sdaPin, SCLPinNum = sclPin)
            except:
                print  "Error setting the LabJackU3LJTick. Is the device detached?\n\nPython error:" + str(sys.exc_info()[1])
        elif chl == 'B':
            # front panel set voltages
            voltageB = (float(val)-2)/500
            if voltageB < 0: voltageB = 0
            try:
                self.device.i2c(LabJackU3LJTick.DAC_ADDRESS, [49, int(((voltageB*self.bSlope)+self.bOffset)/256), int(((voltageB*self.bSlope)+self.bOffset)%256)], SDAPinNum = sdaPin, SCLPinNum = sclPin)
            except:
                print  "Error setting the LabJackU3LJTick. Is the device detached?\n\nPython error:" + str(sys.exc_info()[1])

    def closeDevice(self):
        if self.device is not None: self.device.close()
     
if __name__ == '__main__':
    lj = LabJackU3LJTick()
    valA = 6
    valB = 0
    lj.setDevice(valA, 'A')
    lj.setDevice(valB, 'B')
    lj.closeDevice()