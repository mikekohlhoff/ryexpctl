'''
Controller for Quantum Composer delay generator
Channels and reference channels are marked on the unit
mapped COM port to be extracted from device manager
CHLA = 1 etc.
'''

import sys
import os
import ctypes
import time
from pyvisa.errors import VisaIOError

class PulseGeneratorSimulator:
    '''simulator, if visa not present or OS not Windows'''
    def __init__(self):
        self.lastCommand = None

    def write(self, string):
        '''visa command write function'''
        self.lastCommand = string

    def read(self):
        '''visa command read function'''
        return self.lastCommand

    def close(self): pass


class PulseGeneratorController:
    '''interface to delay generator'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            import visa
            if sys.platform == 'darwin':
                raise OSError
            rm = visa.ResourceManager()
            self.__delayGen = rm.open_resource('ASRL4::INSTR')
            # set termination character (<carriage return><line feed>, <cr><lf>) for QC delay generator
            self.__delayGen.write_termination=u'\r\n'
            self.__delayGen.read_termination=u'\r\n'
            # time for receiving, processing, responding at 115200 ~10ms, 30ms timeouts sometimes
            self.__delayGen.query_delay = 0.05
            # default baud rate for usb is 38400
            self.__delayGen.baud_rate = 38400
            print 'Visa driver for 9520 delay generator found, connection established with:'
            print self.__delayGen.query('*IDN?')
            self.screenUpdate('ON')
        except OSError:
            self.__delayGen = PulseGeneratorSimulator()
            print 'OSError, enter simulation mode for delay generator'
        except ImportError:
            self.__delayGen = PulseGeneratorSimulator()
            print 'Hardware not present, enter simulation mode for delay generator'


    # When this command is issued the response ok is added to the next read-out
    # but read out after this command times out >50%
    def screenUpdate(self, state):
        '''turn on automatic update of the screen'''
        print 'Screen update of pulse generator turned ' + state
        ret = ''
        while 'ok' not in ret:
            try:
                ret = self.__delayGen.query(':DISPLAY:MODE ' + state)
            except VisaIOError: pass

    def switchChl(self, channel, state):
        self.__delayGen.query(':PULS{:d}:STAT {:d}'.format(channel, state))

    def setDelay(self, channel, delayVal):
        '''set delay of respective channel'''
        # delay set in s
        self.__delayGen.query(":PULS{:d}:DELAY {:1.11f}".format(channel, delayVal))

    def readDelay(self, channel):
        '''read delay of respective channel'''
        try:
            ret = self.__delayGen.query(":PULS{:d}:DELAY?".format(channel))
        except VisaIOError:
            ret = 0
        return ret

    def setWidth(self, channel, widthVal):
        '''set delay of respective channel'''
        # pulse width set in s
        self.__delayGen.query(":PULS{:d}:WIDTH {:1.11f}".format(channel, widthVal))

    def closeConnection(self):
        print 'Delay generator released'
        self.__delayGen.close()

if __name__ == '__main__':
    delGen = PulseGeneratorController()
    #delGen.screenUpdate('ON')
    import time
    chl = 6
    delGen.switchChl(chl, False)
    print delGen.readDelay(chl)
    time.sleep(4)
    delGen.switchChl(chl, True)
    time.sleep(4)
    dl = float(delGen.readDelay(chl))
    delGen.setDelay(chl, 0.0069)
    print delGen.readDelay(chl)
    time.sleep(4)
    delGen.setDelay(chl, dl)
    print delGen.readDelay(chl)
    delGen.closeConnection()
