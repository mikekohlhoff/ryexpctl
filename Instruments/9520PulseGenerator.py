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

   
class PulseGeneratorController:
    '''interface to delay generator'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            import visa
            from pyvisa.resources import MessageBasedResource
            if sys.platform == 'darwin':
                raise OSError
            rm = visa.ResourceManager()
            self.__delayGen = rm.open_resource('ASRL13::INSTR')
            # set termination character (<carriage return><line feed>, <cr><lf>) for QC delay generator
            self.__delayGen.write_termination='\r\n'
            self.__delayGen.read_termination='\r\n'
            # default baud rate for usb is 38400
            self.__delayGen.baud_rate = 38400
            print 'Visa driver for 9520 delay generator found, connection established with:'
            self.__delayGen.write('*IDN?')
            time.sleep(0.1)
            print(self.__delayGen.read())

        except OSError:
            self.__delayGen = PulseGeneratorSimulator()
            print 'OSError, enter simulation mode for delay generator'
        except ImportError:
            self.__delayGen = PulseGeneratorSimulator()
            print 'Hardware not present, enter simulation mode for delay generator'


    def screenUpdate(self, updONOFF):
        '''turn on automatic update of the screen'''
        self.__delayGen.write(':DISPLAY:MODE ' + updONOFF)

    def enableChl(self, channel):
        self.__delayGen.write(':PULS{:d}:STAT 1'.format(channel))

    def disableChl(self, channel):
        self.__delayGen.write(':PULS{:d}:STAT 0'.format(channel))

    def setDelay(self, channel, delayVal):
        '''set delay of respective channel'''
        # delay set in s 
        self.__delayGen.write(":PULS{:d}:DELAY {:f}".format(channel, delayVal))

    def setWidth(self, channel, widthVal):
        '''set delay of respective channel'''
        # pulse width set in s 
        self.__delayGen.write(":PULS{:d}:WIDTH {:f}".format(channel, widthVal))
        
    def closeConnection(self):
        self.__delayGen.close()


if __name__ == '__main__':
    delGen = PulseGeneratorController()
    import time
    delGen.screenUpdate('ON')
    delGen.disableChl(7)
    time.sleep(2)
    delGen.enableChl(7)
    time.sleep(1)
    delGen.setDelay(7, 0.001)
    time.sleep(1)
    delGen.setDelay(7, 0)
    time.sleep(1)
    delGen.setWidth(7, 0.001)
    time.sleep(1)
    delGen.setWidth(7, 0.000001)
    delGen.closeConnection()
