# -*- coding: utf8 -*-

import sys
#import gtk.glade
import ctypes
import platform
import numpy as np
import time
import math

# if PCI board (.dll's) is not present
class DIOCardSimulator:
    def Register_Card(self, CardID, CardNumber): pass
    def DO_7300B_Config(self, CardNumber, PortWidth, TrigSource, WaitStatus,
                        Terminator, O_Cntrl_Pol, FifoThreshold): pass
    def DO_ContWritePort(self, CardNumber, Port, Buffer, WriteCount, Iterations,
        SampleRate, SyncMode): 
        return 'No error, DIO card simulator mode'
    def DO_ReadPort(self, CardNumber, Port, value): pass
    def Release_Card(self, CardNumber): pass
    def DO_EventCallBack(self, CardNumber, mode, EventType, CallbackAddress): pass
    def DO_AsyncClear(self, CardNumber, AccessCnt): pass
    def DO_AsyncCheck(self, CardNumber, Stopped, AccessCnt): pass

class DIOCardController:
    """\
Controller to set ports/lines for PCI7300A DIO card
---------------------------------------------------
Configuration DO32: PORTA (DO16 .. DO31)
                    PORTB (DO0 .. DO15) 
---------------------------------------------------
CHL LEFT at PA 0-9, pins 100-91.  
CHL MID at PA 10-15 and PB 0-3, pins 90-85 and 66-63. 
CHL RIGHT at PB 4-13, pins 62-53.  
Clock bit at PB 14, pin 52 .
---------------------------------------------------
Port width set to 32 (all lines PA+PB)
Card has bandwidth of 20MHz, 80 MBytes/s at 32bit DO. 
---------------------------------------------------
Trigger options:
TRIG_INT_PACER, _CLK_10MHz, _CLK_20MHz, _HANDSHAKE, 
_DO_CLK_TIMER_ACK, _DO_CLK_10M_ACK, _DO_CLK_20M_ACK
    """

    def __init__(self):
        '''Reference to PCI7300A created and card configured for creating waveform potentials '''
        print '-----------------------------------------------------------------------------'
        try:
            if sys.platform == 'darwin':
                raise OSError
            self.__DIOCard = ctypes.windll.LoadLibrary("C:\WINDOWS\system32\PCI-Dask.dll")
            mode = "Hardware driver .dll for DIO card found"
        except OSError:
            self.__DIOCard = DIOCardSimulator()
            mode = 'OSError, enter simulation mode for DIO card'
        except AttributeError:
            self.__DIOCard = DIOCardSimulator()
            mode = "Hardware not present, enter simulation mode for DIO card"
        print mode
       
        # see PCI-DASK.h for constants, 14=revA, 15 = revB
        # register card
        self.__CardId = ctypes.c_int16(15) 
        self.__CardNumber = ctypes.c_int16(0)
        self.__regID = self.__DIOCard.Register_Card(self.__CardId, self.__CardNumber)
        print '-----------------------------------------------------------------------------'
        print 'PCI7300A card registered: ' + str(self.__regID)

        # configure card for digital output 32bit
        self.__PortWidth = ctypes.c_uint16(32)
        
        # 5: 20MHz, 8: 20MHz ACK
        self.__TrigSource = ctypes.c_uint16(5) 
        
        # set to WAIT_TRG {1}
        self.__WaitStatus = ctypes.c_uint16(1)
            
        # PortB P7300_TERM_OFF, P7300_TERM_ON: {0,1}
        self.__Terminator = ctypes.c_uint16(0) 
        
        # defined for DOTRIG positive
        self.__O_Cntrl_Pol = ctypes.c_uint16(0x000000000L) 
        
        # if PortWidth = 32
        self.__FifoThreshold = ctypes.c_uint32(0) 

        self.SampleRate = 20000000;
        # time interval used for calculating waveforms
        self.timeStep = 1/float(self.SampleRate)
        # mode A/B: 30, mode B/A: 15
        self.__clockBit = 15

        # callback constants
        self.__EventMode = ctypes.c_int16(0)
        # DO_End
        self.__EventType = ctypes.c_int16(0)
        cb_type = ctypes.CFUNCTYPE(None)
        self.cb_fun = cb_type(self.DOCallBackFunc)

        # DO_ContWritePort constants
        # For (..) PCI-7300A (..) this argument must be set to 0.
        self.__Port = ctypes.c_uint16(0) 
        self.__Iterations = ctypes.c_uint16(1)
        # SYNCH_OP, ASYNCH_OP {1,2} sync when return after digital op completed
        self.__SyncMode = ctypes.c_uint16(2)
        self.__SampleRateIn = ctypes.c_double(1)
        
        configReturn = self.configureCardDO()
        print 'Configured PCI7300A card, return value: ' + str(configReturn)

    def configureCardDO(self): 
        configReturn = self.__DIOCard.DO_7300B_Config(self.__regID, self.__PortWidth, self.__TrigSource, \
                       self.__WaitStatus, self.__Terminator, self.__O_Cntrl_Pol, self.__FifoThreshold)
        return configReturn
        
    def buildDOBuffer(self, potentialsOut):
        # build buffer from generated waveform output
        potentialsOut[potentialsOut < 0] = 0
        # three positive channels
        left = np.uint32(potentialsOut[1,:])
        middle = np.uint32(potentialsOut[3,:])
        right = np.uint32(potentialsOut[5,:])
        # port in order PB/PA configured
        middleSplit = np.zeros(1, dtype=np.uint32)
        self.DOBuffer = np.zeros(np.size(left), dtype=np.uint32)
        # output length for digital output operation
        self.__WriteCount = ctypes.c_uint32(np.size(left))
        # buffer of channels at each time step
        mask = 2**32- 1          
        for i in np.arange(0, np.size(left)):
            # set split channel PB/PA, rotation shift
            middleSplit = (middle[i] << 26 | middle[i] >> 6) & mask
            # 10 bit for each channel
            self.DOBuffer[i] = self.DOBuffer[i] | left[i] << 16 | middleSplit | right[i] << 4
            # set clock bit alternatingly, starting high
            self.DOBuffer[i] = self.DOBuffer[i] | np.fmod(i+1,2) << self.__clockBit
        self.__DOBuffer = np.ascontiguousarray(self.DOBuffer)       
        
        #print '---------------------------------------'
        #print np.size(left)
        #print left[:5]
        #print left[-5:]
        
    def writeWaveformPotentials(self):
        # configure necessary before each output operation
        self.configureCardDO()

        data = ctypes.c_void_p(self.__DOBuffer.ctypes.data)
        Stopped = ctypes.c_bool(False)
        AccessCnt = ctypes.c_uint32(0)
        
        # write data to ports with specified (internal 20MHz) clock
        writeRet = self.__DIOCard.DO_ContWritePort(self.__regID, self.__Port, data, \
        self.__WriteCount, self.__Iterations, self.__SampleRateIn, self.__SyncMode)
        
        Stopped.value=False
        while(not Stopped.value):
            self.__DIOCard.DO_AsyncCheck(self.__regID, ctypes.byref(Stopped),\
            ctypes.byref(AccessCnt))
            #time.sleep(0.001)
        self.__DIOCard.DO_AsyncClear(self.__regID, ctypes.byref(AccessCnt))       
      
    def DOCallBackFunc(self):
        # event callback to clear async register
        # didn't get to work in extTrig mode
        AccessCnt = ctypes.c_uint32()
        self.__DIOCard.DO_AsyncClear(self.__regID, ctypes.byref(AccessCnt))
        
    def changeSampleRate(self, SampleRateIn):
        self.SampleRate = SampleRateIn
        self.timeStep = 1/float(self.SampleRate)

    def releaseCard(self):
        self.__DIOCard.Release_Card(self.__regID)
        print 'PCI7300A released'
