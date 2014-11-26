''' Controller for LeCroy Wavesurfer via VISA (LAN)'''

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


class ScopeSimulator:
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
            time.sleep(0.01)
            data = (np.random.rand(1016) - 0.5)*512
            data = data.astype(np.int16)
            string = struct.pack('1016h', *data) + '\0'
            return string

    def write(self, string):
        '''visa command write function'''
        self.lastCommand = string

class ScopeController:
    '''interface to LeCroy oscilloscopes'''
    def __init__(self):
        try:
            import visa
            self.__scope = visa.instrument("VICP::169.254.201.2::inst0", timeout = 1, values_format = 1)
            print "Scope connection established"
        except ImportError:
            print "can't load visa/scope driver, using simulator"
            self.__scope = ScopeSimulator()


    def initialize(self):
        '''hardware initialization'''
        # CORD LO for intel based computers, CORD HI default
        # waveform setup, data as block of definite length, binary coding as 8bit integers, BIN vs WORD
        self.__scope.write('WFSU SP,0,NP,0,FP,0,SN,0;CFMT DEF9,WORD,BIN;CHDR OFF;CORD HI')
        # clear screen, sweepes and turn of auto cal and leave scope in normal trigger mode
        self.__scope.write('*CLS;CLSW;TRMD NORMAL;ACAL OFF')
        self.__scope.write('DISP OFF')

    def dispOff(self):
        self.__scope.write('DISP OFF')
        
    def dispOn(self):
        self.__scope.write('DISP ON')
                
    def setSweeps(self, numberSweeps):
        '''set number of sweeps for averaging'''
        # doesn"t seem to be neccessary self.__scope.write(''AVG(C1)',AVGTYPE,CONTINUOUS)
        self.__scope.write("VBS 'app.acquisition.C1.AverageSweeps=" + str(numberSweeps) + "'")

    def getDescription(self):
        self.__scope.write('ARM;WAIT;C1:WF? DESC;')
        data = self.__scope.read_raw()
        WAVEDESC = data[16:346+16]
        print struct.unpack(wdf, WAVEDESC)
        return wft._make(struct.unpack(wdf, WAVEDESC))

    def setScales(self):
        wfd = self.getDescription()
        self.yscale = wfd.VERTICAL_GAIN
        self.yoff = wfd.VERTICAL_OFFSET
        print self.yscale, self.yoff

    def armwaitread(self):
        self.__scope.write('ARM;WAIT;C1:WF? DAT1')
        data = self.__scope.read_raw()
        return 1.*np.fromstring(data[16:-1], dtype=np.int16)*self.yscale+self.yoff
    
    def armScope(self):
        '''arm scope for single shot acquisition'''
        # set scope to 1 average before and single trigger mode
        self.setSweeps(1)
        self.__scope.write('*CLS;CLSW;TRMD NORMAL')

    def getTrace(self, channel):
        '''measure trace from scope, using channel number "channel"'''
        self.__scope.write('C1:WF? ALL;')
        #self.__scope.write('C1:WF? DAT')

        data = self.__scope.read_raw()
        print 'string length:', len(data)
        print 'string start: ', data[:100]#
        print 'hex start: ', data[:100].encode('hex')

        WAVEDESC = data[15:346+15]
        struct.unpack(wdf, WAVEDESC)
        return data

        npa = np.fromstring(data[16:-1], dtype=np.short)
        
        from matplotlib import pyplot as plt
        plt.plot(npa)
        plt.show()
        return data
        #print(data)

		
if __name__ == '__main__':	
    pass
