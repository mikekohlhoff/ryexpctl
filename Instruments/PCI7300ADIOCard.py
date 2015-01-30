# -*- coding: utf8 -*-

import sys
#import gtk.glade
import ctypes
import platform
import numpy as np
import matplotlib.pyplot as plt
import textwrap
import time

from WaveformPotentials import WaveformPotentials21Elec

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
       

        # see PCI-DASK.h for constants
        # 14=revA, 15 = revB
        self.__CardId = ctypes.c_int16(15) 
        self.__CardNumber = ctypes.c_int16(0)
        self.__DIOCard.Register_Card(self.__CardId, self.__CardNumber)

        # configure card for digital output 32bit
        self.__PortWidth = ctypes.c_uint16(32)
        
        # 5: 20MHz, 8: 20MHz ACK
        self.__TrigSource = ctypes.c_uint16(5) 
        
        # set to WAIT_TRG {1}
        self.__WaitStatus = ctypes.c_uint16(1)
            
        # PortB P7300_TERM_OFF, P7300_TERM_ON: {0,1}
        self.__Terminator = ctypes.c_uint16(1) 
        
        # defined for DOTRIG positive
        self.__O_Cntrl_Pol = ctypes.c_uint16(0x000000000L) 
        
        # if PortWidth = 32
        self.__FifoThreshold = ctypes.c_uint32(0) 

        self.SampleRate = 20000000;
        # time interval used for calculating waveforms
        self.timeStep = 1/float(self.SampleRate)
        # mode A/B: 30, mode B/A: 15
        self.__clockBit = 15

    def configureCardDO(self): 
        configReturn = self.__DIOCard.DO_7300B_Config(self.__CardNumber, self.__PortWidth, self.__TrigSource, \
                       self.__WaitStatus, self.__Terminator, self.__O_Cntrl_Pol, self.__FifoThreshold)

    def changeSampleRate(self, SampleRateIn):
        self.SampleRate = SampleRateIn
        self.timeStep = 1/float(self.SampleRate)

    def buildDOBuffer(potentialsOut):
        # build buffer from generated waveform output
        # three positive channels
        left = np.uint32(potentialsOut[1,:])
        middle = np.uint32(potentialsOut[3,:])
        right = np.uint32(potentialsOut[5,:])
    
        # port in order PB/PA configured
        middleSplit = np.zeros(1, dtype=np.uint32)
        self.DOBuffer = np.zeros(np.size(left), dtype=np.uint32)

        self.WriteCount = np.size(left)
        # buffer of channels at each time step
        mask = 2**32- 1
        for i in np.arange(0, np.size(left)):
            # set split channel PB/PA, rotation shift
            middleSplit = (middle[i] << 26 | middle[i] >> 6) & mask
            # 10 bit for each channel
            self.DOBuffer[i] = self.DOBuffer[i] | left[i] << 16 | middleSplit | right[i] << 4
            # set clock bit alternatingly, starting high
            self.DOBuffer[i] = self.DOBuffer[i] | np.fmod(i+1,2) << self.__clockBit


    def writeWaveformPotentials(self, potentialsOut):
        # For (..) PCI-7300A (..) this argument must be set to 0.
        Port = ctypes.c_uint16(0) 
        # length of the buffer
        WriteCount = ctypes.c_uint32(self.WriteCount)
        Iterations = ctypes.c_uint16(1)
        # SYNCH_OP, ASYNCH_OP {1,2} sync when return after digital op completed
        SyncMode = ctypes.c_uint16(2)
        SampleRate = ctypes.c_double(1)
        # write data to ports with specified (internal) clock
        writeRet = self.__DIOCard.DO_ContWritePort(self.__CardNumber, Port, ctypes.c_void_p(self.DOBuffer.ctypes.data), \
                                        WriteCount, Iterations, SampleRate, SyncMode)

    def releaseCard(self):
        self.__DIOCard.Release_Card(self.__CardNumber)
        print 'PCI7300A released'
        
if __name__ == "__main__":
    # some radio button for port configuration BA/AB
    DIOCard = DIOCardController()
    DIOCard.configureCard(True)
    print DIOCard.SampleRate
    print DIOCard.timeStep
    DIOCard.changeSampleRate(10000000)
    print DIOCard.timeStep
    print DIOCard.SampleRate
    wfPotentials = WaveformPotentials21Elec()
    maxAmp = 1023/2.0
    vInit = 700
    vFinal = 700
    decelDist = 19.1
    inTime = 1
    outDist = 0
    outTime = 0
    # build waveform potentials
    wfPotentials.generate(DIOCard.timeStep, vInit, vFinal, inTime, outTime, maxAmp, decelDist)
    #wfPotentials.plot()
    print DIOCard.writeWaveformPotentials(wfPotentials.potentialsOut)
    DIOCard.releaseCard()

