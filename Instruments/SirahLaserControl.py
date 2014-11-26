''' Controller for Sirah Dye Laser'''

import sys
import os
import ctypes

class SirahLaserSimulator:
    '''simulator, if dll not present or OS not Windows'''
    def __init__(self, LaserType):
        self.__LaserType = LaserType
    def LaserCreate(self, FileName, ObjPtr):
        return 0
    def LaserGetLastError(self, buf_length, errorText): pass
    def LaserDestroy(self, ObjPtr): pass
    def LaserGet(self, ObjPtr, nPositionMode, dPosition):
        dPosition = 666
        return 0
    def LaserGoto(self, ObjPtr, nPositionMode, dPosition, dBacklashMode):
        return 0
    def LaserConfigurationSetDouble(self, ObjPtr, sectionIn, keyIn, valueIn):
        return 0
    def LaserConfigurationSetInt(self, ObjPtr, sectionIn, keyIn, valueIn):
        return 0
    def LaserScanBurstStart(self, ObjPtr): pass
    def LaserScanBurstNext(self, ObjPtr, nPositionMode, dPosition, bContinue):
        dPosition = 666
        bContinue = 1
        return 0
    def LaserScanBurstCancel(self, ObjPtr): pass
        
class SirahLaserController:
    '''interface to USB87P4'''
    def __init__(self, LaserType):
        try:
            if sys.platform == 'darwin':
                raise OSError
            self.__SirahLaser = ctypes.cdll.LoadLibrary(os.getcwd() + '\SirahLaserObject.dll')
            mode = 'Hardware driver .dll found'
        except OSError:
            self.__SirahLaser = SirahLaserSimulator(LaserType)
            mode = 'OSError, enter simulation mode'
        except AttributeError:
            self.__SirahLaser = SirahLaserSimulator(LaserType)
            mode = 'Hardware not present, enter simulation mode'

        self.__LaserType = LaserType
        self.__FileName = ctypes.c_char_p(os.getcwd() + '\Sirah Control ' + LaserType + '\Sirah Laser.ini')
        self.__ObjPtr = ctypes.c_uint32()
        self.__nPositionMode = ctypes.c_int16(0)
        self.__dBacklashMode = ctypes.c_int16(0)

    def OpenLaser(self):
        '''Create reference to laser'''
        ret = self.__SirahLaser.LaserCreate(self.__FileName, ctypes.byref(self.__ObjPtr))
        if ret != 0:
            self.GetLastError()
            print "Consider port being blocked by reference not properly close"

    def GetLastError(self):
        '''Error handling if return !=0'''
        buf_length = 2000
        errorText = ctypes.create_string_buffer(buf_length)
        ret = self.__SirahLaser.LaserGetLastError(ctypes.c_int16(buf_length), errorText)
        print "============================================================="
        print "An error occured in SirahLaser:"
        print str(errorText.value)
        print "-------------------------------------------------------------"
        
    def CloseLaser(self):
        '''Destroy laser reference'''
        self.__SirahLaser.LaserDestroy(self.__ObjPtr)

    def GetWavelength(self):
        '''Read current wavelength'''
        dPosition = ctypes.c_double()
        ret = self.__SirahLaser.LaserGet(self.__ObjPtr, self.__nPositionMode, ctypes.byref(dPosition)); 
        if ret != 0:
            self.GetLastError()
        return dPosition.value

    def Goto(self, GotoIn):
        '''Change wavelength'''
        dPosition = ctypes.c_double(GotoIn)
        self.__SirahLaser.LaserGoto(self.__ObjPtr, self.__nPositionMode, dPosition, self.__dBacklashMode);

    def SetConfigurationDbl(self, sectionIn, keyIn, valueIn):
        '''Writes configuration for burst scan'''
        Section = ctypes.c_char_p(sectionIn)
        Key = ctypes.c_char_p(keyIn)
        Value = ctypes.c_double(valueIn)
        ret = self.__SirahLaser.LaserConfigurationSetDouble(self.__ObjPtr, Section, Key, Value);
        if ret != 0:
            self.GetLastError()
            
    def SetConfigurationInt(self, sectionIn, keyIn, valueIn):
        '''Writes configuration for burst scan'''
        Section = ctypes.c_char_p(sectionIn)
        Key = ctypes.c_char_p(keyIn)
        Value = ctypes.c_int32(valueIn)
        ret = self.__SirahLaser.LaserConfigurationSetInt(self.__ObjPtr, Section, Key, Value);
        if ret != 0:
            self.GetLastError()
    
    def StartBurst(self, Start, End, Increment):
        '''Sets laser into burst mode with prior setting of arguments'''
        self.SetConfigurationDbl('BurstScan', 'FromPosition', Start)
        self.SetConfigurationDbl('BurstScan', 'ToPosition', End)
        self.SetConfigurationDbl('BurstScan', 'Increment', Increment)
        self.SetConfigurationInt('BurstScan', 'Points', 0)
        self.SetConfigurationInt('BurstScan', 'ScanMode', 0)
        self.SetConfigurationInt('BurstScan', 'PositionMode', self.__nPositionMode.value)
        self.__SirahLaser.LaserScanBurstStart(self.__ObjPtr)

    def NextBurst(self):
        '''Increments to next step in burst scan'''
        dPosition = ctypes.c_double()
        bContinue = ctypes.c_int16()
        ret = self.__SirahLaser.LaserScanBurstNext(self.__ObjPtr, self.__nPositionMode, ctypes.byref(dPosition), ctypes.byref(bContinue))
        if ret != 0:
            self.GetLastError()
        return (dPosition.value, bContinue.value != 0)

    def CancelBurst(self):
        '''Cancels burst scan started before by StartBurst()'''
        self.__SirahLaser.LaserScanBurstCancel(self.__ObjPtr);
        
if __name__ == '__main__':
    import time
    UVLaser = SirahLaserController('UV')
    print UVLaser._SirahLaserController__LaserType
    UVLaser.OpenLaser()
    lambdaOld = UVLaser.GetWavelength()
    print 'lambda old ' + str(lambdaOld)
    time.sleep(0.5)
    UVLaser.StartBurst(lambdaOld, lambdaOld+1.0, 0.1)
    cont = True
    while cont:
        (wl, cont) = UVLaser.NextBurst()    
        print wl
        time.sleep(0.2)
    UVLaser.CancelBurst()
    UVLaser.Goto(lambdaOld)
    print UVLaser.GetWavelength()
    UVLaser.CloseLaser()
