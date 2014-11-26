''' Controller for analog output DCON USB 87P4'''

import sys
import os
import ctypes
  
class USBP87P4Controller:
    '''interface to USB87P4'''
    def __init__(self):
        try:
            if sys.platform == 'darwin':
                raise OSError
                print 'OSX'
            self.__DCONDLL = ctypes.windll.LoadLibrary(os.getcwd() + '\DCON_PC.dll')
            self.__UARTDLL = ctypes.windll.LoadLibrary(os.getcwd() + '\Uart.dll')
            mode = 'Hardware driver .dll found'
        except OSError:
            mode = 'OSError, enter simulation mode'
        except AttributeError:
            mode = 'Hardware not present, enter simulation mode'
        print mode
        
if __name__ == '__main__':
    analogOut = USBP87P4Controller()
