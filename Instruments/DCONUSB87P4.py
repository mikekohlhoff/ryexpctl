''' Controller for analog output DCON USB 87P4'''

import sys
import os
import ctypes

class USB87P4Simulator:
    '''simulator, if dll not present or OS not Windows'''
    def __init__(self, dll):
        self.__type = dll
    def Open_Com(self, cComPort, dwBaudRate, cData, cParity, cStop): pass
    def Close_Com(self, cPort): pass
    def DCON_Write_AO(self, cComPort, iAddress, iSlot, iChannel, iAOTotalCh, fValue, iCheckSum, iTimeOut): pass
        
class USB87P4Controller:
    '''interface to USB87P4'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        print "C:\\Users\\TPSgroup\Documents\\RSE Control\\ryexpctl\\Instruments\\Uart.dll"
        print os.getcwd() + r'\Instruments\DCON_PC.dll'
        try:
            if sys.platform == 'darwin':
                raise OSError
            #self.__DCONDLL = ctypes.windll.LoadLibrary("C:\\Users\\TPSgroup\\Documents\\RSE Control\\ryexpctl\\Instruments\\DCON_PC.dll")
            #self.__UARTDLL = ctypes.windll.LoadLibrary("C:\\Users\\TPSgroup\Documents\\RSE Control\\ryexpctl\\Instruments\\Uart.dll")
            self.__DCONDLL = ctypes.windll.LoadLibrary(os.getcwd() + '\Instruments\DCON_PC.dll')
            self.__UARTDLL = ctypes.windll.LoadLibrary(os.getcwd() + '\Instruments\Uart.dll')
            mode = 'Hardware driver .dll for USB87P4 found'
        except OSError:
            self.__DCONDLL = USB87P4Simulator('DCON')
            self.__UARTDLL = USB87P4Simulator('UART')
            mode = 'OSError, enter simulation mode for USB87P4'
        except AttributeError:
            self.__DCONDLL = USB87P4Simulator('DCON')
            self.__UARTDLL = USB87P4Simulator('UART')
            mode = 'Hardware not present, enter simulation mode for USB87P4'
        print mode

        self.__dwBaudRate = ctypes.c_uint32(115200)
        self.__iAddress = ctypes.c_int16(2)
        self.__iSlot = ctypes.c_int16(-1)
        self.__iCheckSum = ctypes.c_int16(0)
        self.__iTimeOut = ctypes.c_int16(100)
        self.__cParity = ctypes.c_uint8(0)
        self.__cStop = ctypes.c_uint8(0)
        self.__cData = ctypes.c_uint8(8)
        self.__iAOTotalCh = ctypes.c_int16(4)
        # com port 7 as in TPS41 layout
        self.__cComPort = ctypes.c_uint8(7)

    def openDevice(self):
        '''hardware initialization'''
        # com port 7 as in TPS41 layout
        try:
            devReturn = self.__UARTDLL.Open_Com(self.__cComPort, self.__dwBaudRate, self.__cData, self.__cParity,
            self.__cStop)
            if str(devReturn) != '0':
                raise IOError
        except IOError:
            print 'Error opening USB87P4 device: ' + str(devReturn)
            #sys.exit()
            return
        print 'Connection to analog output device USB-84P4 established'

    def closeDevice(self):
        '''close device session'''
        self.__UARTDLL.Close_Com(self.__cComPort)
        print "Connection to analog output device USB-84P4 closed"
    
    def writeAOExtraction(self, outputVoltage):
        '''write scaled analog output to channel 0'''
        iChannel = ctypes.c_int16(0)
        fValue = ctypes.c_float((float(outputVoltage)+2)/500)
        self.__DCONDLL.DCON_Write_AO(self.__cComPort,self.__iAddress, self.__iSlot, iChannel,
        self.__iAOTotalCh, fValue, self.__iCheckSum, self.__iTimeOut)
        print 'write extraction port'
    
    def writeAOIonOptic1(self, outputVoltage):
        '''write scaled analog output to channel 1'''
        iChannel = ctypes.c_int16(1)
        fValue = ctypes.c_float((float(outputVoltage)+2)/500)
        self.__DCONDLL.DCON_Write_AO(self.__cComPort, self.__iAddress, self.__iSlot, iChannel,
        self.__iAOTotalCh, fValue, self.__iCheckSum, self.__iTimeOut)
        
    def writeAOMCP(self, outputVoltage):
        '''write scaled analog output to channel 2'''
        iChannel = ctypes.c_int16(2)
        fValue = ctypes.c_float((float(outputVoltage)+2)/500)
        self.__DCONDLL.DCON_Write_AO(self.__cComPort,self.__iAddress, self.__iSlot, iChannel,
        self.__iAOTotalCh, fValue, self.__iCheckSum, self.__iTimeOut)
    
    def writeAOPhos(self, outputVoltage):
        '''write scaled analog output to channel 3'''
        iChannel = ctypes.c_int16(3)
        fValue = ctypes.c_float((float(outputVoltage)+2)/500)
        self.__DCONDLL.DCON_Write_AO(self.__cComPort,self.__iAddress, self.__iSlot, iChannel,
        self.__iAOTotalCh, fValue, self.__iCheckSum, self.__iTimeOut)
         
if __name__ == '__main__':
    analogOut = USB87P4Controller()
    analogOut.openDevice()
    import time
    for i in range(2):
        j = i+1
        analogOut.writeAOMCP(j*100)
        analogOut.writeAOExtraction(j*100)
        analogOut.writeAOPhos(j*100)
        analogOut.writeAOIonOptic1(j*100)
        time.sleep(2)
    j = 0    
    analogOut.writeAOMCP(j*100)
    analogOut.writeAOExtraction(j*100)
    analogOut.writeAOPhos(j*100)
    analogOut.writeAOIonOptic1(0)
    analogOut.closeDevice()
