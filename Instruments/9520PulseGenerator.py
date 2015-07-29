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
            # set termination character (<carriage return><line feed>, <cr><lf>) for QC delay generator
            self.__delayGen = rm.open_resource('ASRL13::INSTR')#, resource_pyclass=MessageBasedResource, send_end=True)
            #self.__delayGen.term_chars='\r\n'
            # default baud rate for usb is 38400

            
            #self.__delayGen.write(':SYST:BAUD 38400')
            print 'Visa driver for 9520 delay generator found, connection established with:'
            #self.__delayGen.write('*IDN?')
            #time.sleep(1)
            #print(self.__delayGen.read())
        except OSError:
            self.__delayGen = PulseGeneratorSimulator()
            print 'OSError, enter simulation mode for delay generator'
        except ImportError:
            self.__delayGen = PulseGeneratorSimulator()
            print 'Hardware not present, enter simulation mode for delay generator'

        


    def enableChl(self, channel):
        self.__delayGen.write("PULSE{:d}:STATE ON".format(channel))

    def disableChl(self, channel):
        self.__delayGen.write("PULSE{:d}:STATE OFF<cr><lf>".format(channel))

    def setDelay(self, channel, delayVal):
        '''set delay of respective channel'''
        # delay set in s 
        self.__delayGen.write("PULSE{:d}:DELAY {:f}<cr><lf>".format(channel, delayVal))


if __name__ == '__main__':
    delayGenerator = PulseGeneratorController()
    import time
    #delayGenerator.enableChl(1)
    time.sleep(2)
    #delayGenerator.disableChl(1)
