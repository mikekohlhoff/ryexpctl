''' Controller for LeCroy HDO scope via VISA and ActiveX DSO over TCPIP/VICP passport (LAN)'''

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


class LeCroyScopeControllerVISA:
    '''interface to LeCroy oscilloscopes controlled by commands sent via VISA'''
    def __init__(self):
        try:
            import visa
            # introduced this fix, cf. pyvisa issue #168
            from pyvisa.resources import MessageBasedResource
            from pyvisa.errors import VisaIOError
            rm = visa.ResourceManager()
            ip_addr = "VICP::169.254.201.2::INSTR"
            self.__scope = rm.open_resource(ip_addr, resource_pyclass=MessageBasedResource)
            # CORD LO for intel based computers, CORD HI default
            # waveform setup, data as block of definite length, binary coding as 8bit integers, BYTE (8-bit) vs WORD (16bit)
            # SP = sparsing
            self.__scope.write('WFSU SP,0,NP,0,FP,0,SN,0;CHDR OFF;CFMT DEF9,WORD,BIN;CORD HI')
            # clear registers, sweepes and turn of auto cal and leave scope in normal trigger mode
            self.__scope.write('*CLS;CLSW;TRMD NORMAL;ACAL OFF')

        except ImportError:
            print "Can't load visa/scope driver"
        except VisaIOError:
            print "Scope is probably turned off"

    def initialize(self):
        '''hardware initialization'''
        print '-----------------------------------------------------------------------------'
        print "Scope connection established with device ID:"
        print(self.__scope.query("*IDN?"))

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

    def setSweeps(self, numberSweeps, remote):
        '''set number of sweeps for averaging for ACQ channels when scope not connected,
           or for math channels when scope remotely controlled and '''

        if remote:
            # set averaging of scope channels
            self.__scope.write("VBS 'app.acquisition.C1.AverageSweeps=1'")
            self.__scope.write("VBS 'app.acquisition.C2.AverageSweeps=1'")
            self.__scope.write('F1:DEFINE SWEEPS,' + str(numberSweeps))
            self.__scope.write('F2:DEFINE SWEEPS,' + str(numberSweeps))
            print 'Avg on math channels set set to ' + str(numberSweeps)
        else:
            # set averaging of scope channels
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
        self.numpointsC1 = wfd.WAVE_ARRAY_COUNT
        self.timeincrC1 = wfd.HORIZ_INTERVAL
        self.trigOffsetC1 =  wfd.HORIZ_OFFSET
        self.trigDelay = self.__scope.query('TRIG_DELAY?')
        wfd = self.getWFDescription('C2')
        self.yscaleC2 = wfd.VERTICAL_GAIN
        self.yoffC2 = wfd.VERTICAL_OFFSET
        self.numpointsC2 = wfd.WAVE_ARRAY_COUNT
        self.timeincrC2 = wfd.HORIZ_INTERVAL
        self.trigOffsetC2 =  wfd.HORIZ_OFFSET

    def armwaitread(self, acqcnt, avgsweeps):
        '''Readout math channels and clear sweeps to restart
        '''
        # register acquisitions
        self.__scope.write('ARM;WAIT;')

        if acqcnt % avgsweeps == 0:
            # read binary data as 16bit integer ('h', WORD)
            data1 = (np.asarray(self.__scope.query_binary_values('C1:WF? DAT1', datatype='h', is_big_endian=True)).astype('float'))*self.yscaleC1-self.yoffC1
            data2 = (np.asarray(self.__scope.query_binary_values('C2:WF? DAT1', datatype='h', is_big_endian=True)).astype('float'))*self.yscaleC2-self.yoffC2
            self.clearSweeps()
        else:
            data1 = []
            data2 = []

        return [data1, data2]

    def readmathchl(self):
        # read internal state change register
        inr = self.__scope.write("INR?")
        print str(inr)
        # processing on F1 has finished
        if inr == 256:
            self.__scope.write('F1:WF? DAT1')
            data1 = self.__scope.read_raw()
            self.__scope.write('F2:WF? DAT1')
            data2 = self.__scope.read_raw()
            self.__scope.write('F1:FRST;F2:FRST')

            datC1 = 1.*(np.fromstring(data1[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscaleC1-self.yoffC1
            datC2 = 1.*(np.fromstring(data2[16:-1], dtype=np.dtype('>i1')).astype('float'))*self.yscaleC2-self.yoffC2
        else:
            datC1 = []
            datC2 = []

        return [datC1, datC2]

    def invertTrace(self, boolInv):
        self.__scope.write("VBS? 'app.Acquisition.C1.Invert=" + str(boolInv) + "'")
        self.__scope.write("VBS? 'app.Acquisition.C2.Invert=" + str(boolInv) + "'")
        time.sleep(0.2)
        if boolInv:
            print 'Scope trace inverted'
        else:
            print 'Scope trace non-inverted'

    def closeConnection(self):
        self.__scope.close()

    def buzzBeep(self):
        self.__scope.write("BUZZ BEEP")
        print 'Measurement finished'


if __name__ == '__main__':
    scope = LeCroyScopeControllerVISA()
    scope.initialize()
    scope.dispOff()
    time.sleep(4)
    scope.dispOn()
    scope.closeConnection()
