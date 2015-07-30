''' Controller for LeCroy Wavesurfer via VISA and ActiveX DSO over TCPIP/VICP passport (LAN)'''

import numpy as np
import struct
from collections import namedtuple
import random
import time

wdf = '!16x 16x H H 1L 4x 4x 4x 4x 4x L 4x 4x 4x 16x 4x 16x 4x L 12x L 16x 4x 2f 8x H 2x f d 8x 48x 48x f 16x 4x 4x 4x H H f H H f f H'
# COMM_TYPE, COMM_ORDER, WAVE_DESCRIPTOR, WAVE_ARRAY, WAVE_ARRAY_COUNT, FIRST_POINT, VERTICAL_GAIN, VERTICAL_OFFSET, NOMINAL_BITS,
# HORIZ_INTERVAL, HORIZ_OFFSET, HORIZ_UNCERTAINTY, TIMEBASE, VERT_COUPLING, PROBE_ATT, FIXED_VERT_GAIN, BW_LIMIT, VERTICAL_VERNIER,
# ACQ_VERT+PFFSET, WAVE_SOURCE 
wft = namedtuple('waveformDesc', 'COMM_TYPE, COMM_ORDER, WAVE_DESCRIPTOR, WAVE_ARRAY,\
                  WAVE_ARRAY_COUNT, FIRST_POINT, VERTICAL_GAIN, VERTICAL_OFFSET, NOMINAL_BITS,\
                  HORIZ_INTERVAL, HORIZ_OFFSET, HORIZ_UNCERTAINTY, TIMEBASE, VERT_COUPLING,\
                  PROBE_ATT, FIXED_VERT_GAIN, BW_LIMIT, VERTICAL_VERNIER, ACQ_VERT_PFFSET, WAVE_SOURCE')

class LeCroyScopeSimulatorVISA:
    '''simulator, if visa is not present'''
    def __init__(self):
        self.lastCommand = None

    def read(self): 
        '''visa command read function'''
        return self.lastCommand

    def read_raw(self):
        if self.lastCommand == 'ARM;WAIT;C1:WF? DESC;':
            data = 16*'.' + struct.pack(wdf, 0, 0, 346, 8000, 1000, 0, 1, 0, 11, 1, 0, 0, 1, 1, 1, 1,1,1, 1, 1)
            return data

        elif self.lastCommand == 'ARM;WAIT;C1:WF? DAT1':
            time.sleep(.1)
            data = (np.random.rand(1016) - 0.5)*512
            data = data.astype(np.int16)
            string = struct.pack('1016h', *data) + '\0'
            return string

    def write(self, string):
        '''visa command write function'''
        self.lastCommand = string

class LeCroyScopeControllerVISA:
    '''interface to LeCroy oscilloscopes controlled by commands sent via VISA'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            import visa
            # introduced this fix, cf. pyvisa issue #168
            from pyvisa.resources import MessageBasedResource
            rm = visa.ResourceManager()
            self.__scope = rm.open_resource("VICP::169.254.201.2::INSTR", resource_pyclass=MessageBasedResource)
            print "Scope connection established with device ID:"
            print(self.__scope.query("*IDN?"))
        except ImportError:
            print "Can't load visa/scope driver, using simulator for scope"
            self.__scope = LeCroyScopeSimulatorVISA()


    def initialize(self):
        '''hardware initialization'''
        # do a calibration
        self.__scope.write('*CAL?')
        time.sleep(5)
        # CORD LO for intel based computers, CORD HI default
        # waveform setup, data as block of definite length, binary coding as 8bit integers, BIN vs WORD (16bit)
        self.__scope.write('WFSU SP,1,NP,0,FP,0,SN,0;CFMT DEF9,BYTE,BIN;CHDR OFF;CORD HI')
        # clear registers, sweepes and turn of auto cal and leave scope in normal trigger mode
        self.__scope.write('*CLS;CLSW;TRMD NORMAL;ACAL OFF')

    def trigModeNormal(self):
        self.__scope.write('TRMD NORMAL')
    
    def dispOff(self):
        self.__scope.write('DISP OFF')
        print 'Scope display off'
        
    def dispOn(self):
        self.__scope.write('DISP ON')
        print 'Scope display on'
                
    def setSweeps(self, numberSweeps):
        '''set number of sweeps for averaging'''
        self.__scope.write("VBS 'app.acquisition.C1.AverageSweeps=" + str(numberSweeps) + "'")

    def clearSweeps(self):
        self._scope.write('*CLS;CLSW')

    def getWFDescription(self):
        self.__scope.write('C1:WF? DESC;')
        data = self.__scope.read_raw()
        WAVEDESC = data[16:346+16]
        return wft._make(struct.unpack(wdf, WAVEDESC))

    def setScales(self):
        wfd = self.getWFDescription()
        self.yscale = wfd.VERTICAL_GAIN
        self.yoff = wfd.VERTICAL_OFFSET
        numpoints = wfd.WAVE_ARRAY_COUNT
        self.timeincr = wfd.HORIZ_INTERVAL
             
    def armwaitread(self):
        '''main function for readout in GUI'''
        self.__scope.write('ARM;WAIT;C1:WF? DAT1')
        data = self.__scope.read_raw()
        return 1.*(np.fromstring(data[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscale-self.yoff

    def getTimeTrace(self):
        '''return trace with time'''
        self.__scope.write('C1:WF? DAT1')
        data = self.__scope.read_raw()
        waveform = (np.fromstring(data[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscale-self.yoff
        plotTime = 1.*np.arange(np.size(waveform))*self.timeincr
        return (plotTime, waveform)

    def closeConnection(self):
        self.__scope.close()

    def buzzBeep(self):
        self.__scope.write("BUZZ BEEP")
        print 'Measurement finished'
    

class LeCroyScopeSimulatorDSO:
    '''simulator for DSO controller, if win32com is not present'''
    def __init__(self):
        self.lastCommand = None

    def ReadString(self, readLen): 
        '''visa command read function'''
        return self.lastCommand

    def ReadBinary(self):
        data = (np.random.rand(1016) - 0.5)*512
        data = data.astype(np.int16)
        string = struct.pack('1016h', *data) + '\0'
        return string

    def WriteString(self, string, constX):
        '''visa command write function'''
        self.lastCommand = string

class LeCroyScopeControllerDSO:
    '''interface to LeCroy oscilloscopes with ActiveX DSO interface for VICP'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            #imports the pywin32 library
            import win32com.client
            self.__scope=win32com.client.Dispatch("LeCroy.ActiveDSOCtrl.1")
            self.__scope.MakeConnection("IP:169.254.201.2")
            self.__scope.WriteString("*IDN?", 1)
            print "Scope connection established with device ID:"
            print(self.__scope.ReadString(256))
        except ImportError:
            print "Can't load scope driver, using simulator for scope"
            self.__scope = LeCroyScopeSimulatorDSO()


    def initialize(self):
        '''hardware and waveform initialization'''
        # do a calibration
        self.__scope.WriteString('*CAL?', 1)
        time.sleep(5)
        # clear screen, sweepes and turn of auto cal and leave scope in normal trigger mode
        self.__scope.WriteString('*CLS;CLSW;TRMD NORMAL;ACAL OFF', 1)
        # CORD LO for intel based computers, CORD HI default
        # waveform setup, data as block of definite length, binary coding as 8bit integers, BIN vs WORD (16bit)
        self.__scope.WriteString('WFSU SP,0,NP,0,FP,0,SN,0;CFMT DEF9,WORD,BIN;CORD HI', 1)
        
    def trigModeNormal(self):
        self.__scope.WriteString('TRMD NORMAL', 1)

    def dispOff(self):
        self.__scope.WriteString('DISP OFF', 1)
        print 'Turn scope display off'
        
    def dispOn(self):
        self.__scope.WriteString('DISP ON', 1)
        print 'Turn scope display on'
                
    def setSweeps(self, numberSweeps):
        '''set number of sweeps for averaging'''
        self.__scope.WriteString("VBS 'app.acquisition.C1.AverageSweeps=" + str(numberSweeps) + "'", 1)

    def clearSweeps(self):
        self._scope.WriteString('*CLS;CLSW', 1)

    def setScales(self):
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.VerticalResolution", 1)
        VerticalResolution = self.__scope.ReadString(256)
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.VerticalPerStep", 1)
        VerticalPerStep = self.__scope.ReadString(256)
        # TODO how to reconstruct screen display from these values
        self.yscale = VerticalResolution
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.VerOffset", 1)
        self.yoff = self.__scope.ReadString(256)
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.Out.Result.Samples' ", 1)
        self.numpoints = self.__scope.ReadString(256)
        self.__scope.WriteString('TDIV?', 1)
        self.timeincr = float(self.__scope.ReadString(256))/(float(self.numpoints)/10)
       
    def armwaitread(self):
        self.__scope.WriteString("ARM;WAIT;C1:WF? DAT1", True)
        data = self.__scope.ReadBinary(self.numpoints)
        data = 1.*np.fromstring(data, dtype=np.int16)
        return data[16:-1]
               
    def getTimeTrace(self):
        return self.__scope.GetScaledWaveformWithTimes("C1", self.numpoints, 0)

    def closeConnection(self):
        self.__scope.Disconnect()

    def buzzBeep(self):
        self.__scope.WriteString("BUZZ BEEP", 1)
        print 'Measurement finished'

		
if __name__ == '__main__':	
    scope = LeCroyScopeControllerDSO()
    scope.initialize()
    scope.setSweeps(1)
    scope.setScales()
    scope.dispOff()
    accumT = 0
    for i in xrange(1,10):
        start = time.clock()
        data = scope.armwaitread()
        accumT = accumT + (time.clock() - start)*1000
        print (accumT/i)
    from matplotlib import pyplot as plt
    plt.figure(1)
    plt.plot(data, '.')
    plt.figure(2)
    time,data = scope.getTimeTrace()
    plt.plot(time,data)
    plt.show()
    scope.buzzBeep()
    scope.dispOn()
    scope.closeConnection()
