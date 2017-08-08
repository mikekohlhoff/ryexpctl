'''
Interface to read out wavemeter accessed via
linked serial port
'''

import sys
import os
import time
from pyvisa.errors import VisaIOError
import serial

class WavemeterReadSimulator:
    '''simulator, if device, visa not present or OS not Windows'''
    def __init__(self):
        self.lastCommand = "1_999.9999992_666.666666"

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
            from pyvisa.resources import MessageBasedResource
            if sys.platform == 'darwin':
                raise OSError
            rm = visa.ResourceManager()
            self.__connection = rm.open_resource('ASRL6::INSTR')
            self.__connection.read_termination='\r'
            self.__connection.baud_rate = 9600
            # ascii encoding throws error
            self.__connection.encoding = "latin-1"
            # tests if port active
            self.__connection.read()
            print 'Wavemeter ouput accessed'

        except OSError:
            self.__connection = WavemeterReadSimulator()
            print 'OSError, enter simulation mode for wavemeter'
        except (ImportError, VisaIOError) as err:
            self.__connection = WavemeterReadSimulator()
            print 'Hardware not present, enter simulation mode for wavemeter'

    def getWavelength(self):
        """Return readings from wavemeter
           When the same wavelength is returned, repeat reading
        """
        # if readout delay is high, overrun error can occur
        asrl_read = False
        while not asrl_read:
            try:
                wl1 = self.__connection.read()
                wl2 = self.__connection.read()
                asrl_read = True
            except VisaIOError:
                pass

        # treat case when both readings are the same wavelength
        if "1_" in wl1 and "2_" in wl2:
            UV = wl1
            IR = wl2
        elif "1_" in wl2 and "2_" in wl1:
            UV = wl2
            IR = wl1
        else: pass
            #UV, IR = self.getWavelength()

        # truncate wavelength from prefix on, assume 6 decimals
        if "1_" in UV:
            UV = UV.split("1_")[1][:10]
            IR = IR.split("2_")[1][:10]

        # replace separator
        UV.replace(",", ".")
        IR.replace(",", ".")

        return [UV, IR]

    def closeConnection(self):
        print 'Wavemeter readout connection closed'
        self.__connection.close()

if __name__ == '__main__':
    import time
    import random
    wvm = WavemeterReadController()
    for i in range(50):
        UV, IR = wvm.getWavelength()
        print "UV wavlength: {:s}nm".format(UV)
        print "IR wavlength: {:s}nm".format(IR)
        print "---------------------------"
        time.sleep(random.uniform(0.1,3))
    wvm.closeConnection()
