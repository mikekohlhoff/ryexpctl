'''
Interface to read out wavemeter accessed via
linked serial port
'''

import sys
import os
import ctypes
import time
from pyvisa.errors import VisaIOError

class WavemeterReadSimulator:
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

class WavemeterReadController:
    '''interface to serial port wavemeter output'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            import visa
            if sys.platform == 'darwin':
                raise OSError
            rm = visa.ResourceManager()
            self.__fnGen = rm.open_resource('ASRL6::INSTR')
            print 'Wavemeter ouput accessed, connection established with:'
            print self.__fnGen.query('*IDN?')

        except OSError:
            self.__fnGen = WavemeterReadSimulator()
            print 'OSError, enter simulation mode for wavemeter'
        except ImportError:
            self.__fnGen = WavemeterReadSimulator()
            print 'Hardware not present, enter simulation mode for wavemeter'

    def getWavelength(self, chl):
        """Enable function output"""
        self.__fnGen.write("OUTP{:d} ON".format(chl))


    def closeConnection(self):
        print 'Wavemeter readout closed'
        self.__fnGen.close()

if __name__ == '__main__':
    import time
    wvm = WavemeterReadController()
    time.sleep(2)
    wvm.closeConnection()
