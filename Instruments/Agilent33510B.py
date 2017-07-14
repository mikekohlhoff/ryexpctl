'''
Controller for Agilent/Keysight 33510B Arbitrary Waveform
generator 2 Chl/20MHz
'''

import sys
import os
import ctypes
import time
from pyvisa.errors import VisaIOError

class WaveformGeneratorSimulator:
    '''simulator, if device, visa not present or OS not Windows'''
    def __init__(self):
        self.lastCommand = None

    def write(self, string):
        '''visa command write function'''
        self.lastCommand = string

    def read(self):
        '''visa command read function'''
        return self.lastCommand

    def close(self): pass

class WaveformGeneratorController:
    '''interface to function generator'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            import visa
            if sys.platform == 'darwin':
                raise OSError
            rm = visa.ResourceManager()
            self.__fnGen = rm.open_resource('USB0::0x0957::0x2607::MY52201121::INSTR')
            print 'Waveform generator found, connection established with:'
            print self.__fnGen.query('*IDN?')

        except OSError:
            self.__fnGen = WaveformGeneratorSimulator()
            print 'OSError, enter simulation mode for delay generator'
        except ImportError:
            self.__fnGen = WaveformGeneratorSimulator()
            print 'Hardware not present, enter simulation mode for delay generator'

    def switchOutput(self, chl, state):
        """Enable/diable function output"""
        if state:
            self.__fnGen.write("OUTP{:d} ON".format(chl))
        else:
            self.__fnGen.write("OUTP{:d} OFF".format(chl))

    def setPulse(self, channel, width, amplitude):
        """Set pulse shape of respective channel"""
        # set burst mode
        self.__fnGen.write("SOUR{:d}:BURS:STAT ON".format(channel))
        self.__fnGen.write("SOUR{:d}:BURS:MODE TRIG".format(channel))
        self.__fnGen.write("SOUR{:d}:BURS:NCYC 1".format(channel))

        # set frequency to 1kHz
        self.__fnGen.write("SOUR{:d}:FREQ 1000".format(channel))

        # set pulse width (s)
        if width < 1E-6:
            width = 1E-6
        self.__fnGen.write("SOUR{:d}:FUNC:PULS:WIDT {:.6f}".format(channel, width))

        # set ramps lead and trail (ns)
        self.__fnGen.write("SOUR{:d}:FUNC:PULS:TRAN:BOTH MIN".format(channel))

        # set voltage levels from 0V to +amplitude V
        if amplitude < 0.002:
            amplitude = 0.002
        self.__fnGen.write("SOUR{:d}:VOLT:LOW 0".format(channel))
        self.__fnGen.write("SOUR{:d}:VOLT:HIGH {:.3f}".format(channel, amplitude))

    def closeConnection(self):
        print 'Waveform generator released'
        self.__fnGen.close()

if __name__ == '__main__':
    import time
    fnGen = WaveformGeneratorController()
    fnGen.setPulse(1, 15E-6, 40E-3)
    time.sleep(2)
    fnGen.setPulse(1, 10E-6, 30E-3)
    time.sleep(2)
    fnGen.setPulse(1, 5E-6, 10E-3)
    time.sleep(2)
    fnGen.switchOutput(1, False)
    time.sleep(2)
    fnGen.switchOutput(1, True)
    fnGen.closeConnection()
