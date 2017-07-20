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
        if self.lastCommand == 'C1:WF? DESC;':
            data = 16*'.' + struct.pack(wdf, 0, 0, 346, 8000, 1000, 0, 1, 0, 11, 1, 0, 0, 1, 1, 1, 1,1,1, 1, 1)
            return data

        elif self.lastCommand == 'C2:WF? DESC;':
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
        try:
            import visa
            # introduced this fix, cf. pyvisa issue #168
            from pyvisa.resources import MessageBasedResource
            from pyvisa.errors import VisaIOError
            rm = visa.ResourceManager()
            self.__scope = rm.open_resource("VICP::169.254.201.2::INSTR", resource_pyclass=MessageBasedResource)
            # CORD LO for intel based computers, CORD HI default
            # waveform setup, data as block of definite length, binary coding as 8bit integers, BIN vs WORD (16bit)
            # SP = sparsing
            self.__scope.write('WFSU SP,0,NP,0,FP,0,SN,0;CFMT DEF9,BYTE,BIN;CHDR OFF;CORD HI')
            # clear registers, sweepes and turn of auto cal and leave scope in normal trigger mode
            self.__scope.write('*CLS;CLSW;TRMD NORMAL;ACAL OFF')

        except ImportError:
            print "Can't load visa/scope driver, using simulator for scope"
            self.__scope = LeCroyScopeSimulatorVISA()
        except VisaIOError:
            print "Scope is probably turned off, enter simulator."
            self.__scope = LeCroyScopeSimulatorVISA()

    def initialize(self):
        '''hardware initialization'''
        print '-----------------------------------------------------------------------------'
        print "Scope connection established with device ID:"
        print(self.__scope.query("*IDN?"))
        # do a calibration
        #self.__scope.write('*CAL?')
        #print 'Calibrating scope ...'
        #time.sleep(8)

    def trigModeNormal(self):
        self.__scope.write('TRMD NORMAL')

    def setTrigOffset(self, offset):
        '''Time on scope display between trigger and left edge'''
        self.__scope.write("VBS 'app.acquisition.Horizontal.HorOffset=" + str(offset) + "'")

    def dispOff(self):
        self.__scope.write('DISP OFF')
        print 'Scope display off'

    def dispOn(self):
        self.__scope.write('DISP ON')
        print 'Scope display on'

    def setSweeps(self, numberSweeps):
        '''set number of sweeps for averaging'''
        self.__scope.write("VBS 'app.acquisition.C1.AverageSweeps=" + str(numberSweeps) + "'")
        self.__scope.write("VBS 'app.acquisition.C2.AverageSweeps=" + str(numberSweeps) + "'")

    def clearSweeps(self):
        self.__scope.write('*CLS;CLSW')

    def getWFDescription(self, channel):
        self.__scope.write('{:s}:WF? DESC;'.format(channel))
        data = self.__scope.read_raw()
        WAVEDESC = data[16:346+16]
        return wft._make(struct.unpack(wdf, WAVEDESC))

    def setScales(self):
        wfd = self.getWFDescription('C1')
        self.yscaleC1 = wfd.VERTICAL_GAIN
        self.yoffC1 = wfd.VERTICAL_OFFSET
        numpointsC1 = wfd.WAVE_ARRAY_COUNT
        self.timeincrC1 = wfd.HORIZ_INTERVAL
        self.trigOffsetC1 =  wfd.HORIZ_OFFSET
        wfd = self.getWFDescription('C2')
        self.yscaleC2 = wfd.VERTICAL_GAIN
        self.yoffC2 = wfd.VERTICAL_OFFSET
        numpointsC2 = wfd.WAVE_ARRAY_COUNT
        self.timeincrC2 = wfd.HORIZ_INTERVAL
        self.trigOffsetC2 =  wfd.HORIZ_OFFSET

    def armwaitread(self):
        '''main function for readout in GUI
           read_raw() doesn't appear to add overhead
           repition rate limitations on scope side
        '''
        self.__scope.write('ARM;WAIT;C1:WF? DAT1')
        data1 = self.__scope.read_raw()
        self.__scope.write('C2:WF? DAT1')
        data2 = self.__scope.read_raw()
        # numpy computation doesn't decrease reading rate
        datC1 = 1.*(np.fromstring(data1[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscaleC1-self.yoffC1
        datC2 = 1.*(np.fromstring(data2[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscaleC2-self.yoffC2
        return [datC1, datC2]

    def getTimeTrace(self):
        '''return trace with time'''
        self.__scope.write('C1:WF? DAT1')
        data = self.__scope.read_raw()
        self.__scope.write('C2:WF? DAT1')
        data1 = self.__scope.read_raw()
        waveform1 = 1.*(np.fromstring(data1[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscaleC1-self.yoffC1
        plotTime1 = 1.*np.arange(np.size(waveform1))*self.timeincrC1
        waveform2 = 1.*(np.fromstring(data2[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscaleC2-self.yoffC2
        plotTime2 = 1.*np.arange(np.size(waveform2))*self.timeincrC2
        return [[plotTime1,waveform1],[plotTime2,waveform2]]

    def invertTrace(self, boolInv):
        self.__scope.write("VBS? 'app.Acquisition.C1.Invert=" + str(boolInv) + "'")
        self.__scope.write("VBS? 'app.Acquisition.C2.Invert=" + str(boolInv) + "'")
        time.sleep(0.5)
        if boolInv:
            print 'Scope trace inverted'
        else:
            print 'Scope trace non-inverted'

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
        try:
            #imports the pywin32 library
            import win32com.client
            self.__scope=win32com.client.Dispatch("LeCroy.ActiveDSOCtrl.1")
            self.__scope.MakeConnection("IP:169.254.201.2")
            # clear screen, sweepes and turn of auto cal and leave scope in normal trigger mode
            self.__scope.WriteString('*CLS;CLSW;TRMD NORMAL;ACAL OFF', 1)
            # CORD LO for intel based computers, CORD HI default
            # waveform setup, data as block of definite length, binary coding as 8bit integers, BIN vs WORD (16bit)
            self.__scope.WriteString('WFSU SP,0,NP,0,FP,0,SN,0;CFMT DEF9,BYTE,BIN;CORD HI', 1)

        except ImportError:
            print "Can't load scope driver, using simulator for scope"
            self.__scope = LeCroyScopeSimulatorDSO()


    def initialize(self):
        '''hardware and waveform initialization'''
        print '-----------------------------------------------------------------------------'
        self.__scope.WriteString("*IDN?", 1)
        print "Scope connection established with device ID:"
        print(self.__scope.ReadString(256))
        # do a calibration
        #self.__scope.WriteString('*CAL?', 1)
        #print 'Calibrating scope ...'
        #time.sleep(8)

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
        self.__scope.WriteString("VBS 'app.acquisition.C2.AverageSweeps=" + str(numberSweeps) + "'", 1)

    def clearSweeps(self):
        self._scope.WriteString('*CLS;CLSW', 1)

    def setScales(self):
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.Out.Result.VerticalResolution", 1)
        self.yscaleC1 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.VerOffset", 1)
        self.yoffC1 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.Out.Result.Samples' ", 1)
        self.numpointsC1 = self.__scope.ReadString(256)
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.Out.Result.HorizontalPerStep", 1)
        self.timeincrC1 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C1.Out.Result.HorizontalOffset", 1)
        self.trigOffsestC1 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C2.Out.Result.VerticalResolution", 1)
        self.yscaleC2 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C2.VerOffset", 1)
        self.yoffC2 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C2.Out.Result.Samples' ", 1)
        self.numpointsC2 = self.__scope.ReadString(256)
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C2.Out.Result.HorizontalPerStep", 1)
        self.timeincrC2 = float(self.__scope.ReadString(256))
        self.__scope.WriteString("VBS? 'return = app.Acquisition.C2.Out.Result.HorizontalOffset", 1)
        self.trigOffsestC2 = float(self.__scope.ReadString(256))

    def armwaitread(self):
        self.__scope.WriteString("ARM;WAIT;C1:WF? DAT1", True)
        data = self.__scope.ReadBinary(self.numpointsC1)
        waveform = 1.*(np.fromstring(data, dtype=np.dtype('int8')).astype('float'))*self.yscaleC1-self.yoffC1
        return waveform

    def getTimeTrace(self):
        waveform =  self.__scope.GetScaledWaveform("C1", self.numpointsC1, 0)
        plotTime = 1.*np.arange(np.size(waveform))*self.timeincrC1
        return (plotTime, waveform)

    def invertTrace(self, chl, boolInv):
        self.__scope.WriteString("VBS? 'app.Acquisition." + chl + ".Invert=" + str(boolInv) + "'", 1)

    def closeConnection(self):
        self.__scope.Disconnect()

    def buzzBeep(self):
        self.__scope.WriteString("BUZZ BEEP", 1)
        print 'Measurement finished'


if __name__ == '__main__':
    scope = LeCroyScopeControllerVISA()
    scope.initialize()
    scope.setSweeps(10)
    scope.setScales()
    scope.invertTrace(True)
    time.sleep(2)
    scope.invertTrace(False)
    time.sleep(1)
    scope.dispOff()
    # accumT = 0
    # for i in xrange(1,20):
    #     start = time.clock()
    #     data = scope.armwaitread()
    #     accumT = accumT + (time.clock() - start)*1000
    #     print (accumT/i)
    # from matplotlib import pyplot as plt
    # plt.figure(1)
    # plt.plot(data)
    # scope.trigModeNormal()
    # plt.figure(2)
    # t, data = scope.getTimeTrace()
    # plt.plot(t, data)
    # plt.show()
    scope.buzzBeep()
    scope.dispOn()
    scope.closeConnection()
