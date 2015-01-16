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

    def configureCard(self, extTrigger):
        # 14=revA, 15 = revB
        self.__CardId = ctypes.c_int16(15) 
        self.__CardNumber = ctypes.c_int16(0) 
        
        # configure card for digital output
        # PortB 0,8,16, or 32 bit port
        self.__PortWidth = ctypes.c_uint16(32)
        
        # I16 __stdcall DO_7300B_Config (U16 CardNumber, U16 PortWidth, U16 TrigSource, U16 WaitStatus, 
        # U16 Terminator, U16 O_Cntrl_Pol, U32 FifoThreshold);
        # TRIG_INT_PACER, TRIG_CLK_10MHz, TRIG_CLK_20MHz, 
        # TRIG_HANDSHAKE, TRIG_DO_CLK_TIMER_ACK, TRIG_DO_CLK_10M_ACK,TRIG_DO_CLK_20M_ACK:
        # {0,1,2,3,4,5,6,7,8}
        self.__TrigSource = ctypes.c_uint16(2) 
        
        # P7300_WAIT_NO, P7300_WAIT_TRG, P7300_WAIT_FIFO, P7300_WAIT_BOTH: {0,1,2,3}
        # set to external triggering {1}
        if extTrigger:
            self.__WaitStatus = ctypes.c_uint16(1)
            print 'DIO card in external trigger mode'
        else:
            self.__WaitStatus = ctypes.c_uint16(0)
            print 'DIO card operated manually'
            
        # PortB P7300_TERM_ON, P7300_TERM_OFF: {0,1}
        self.__Terminator = ctypes.c_uint16(0) 
        
        # P7300_DOREQ_POS, P7300_DOREQ_NEG, P7300_DOACK_POS, P7300_DOACK_NEG
        # P7300_DOTRIG_POS, P7300_DOTRIG_NEG: 0x0000000+{00L,08L,00L,10L,20L,}
        # defined for DOTRIG positive
        self.__O_Cntrl_Pol = ctypes.c_uint16(0x000000000L) 
        
        # if PortWidth = 32
        self.__FifoThreshold = ctypes.c_uint32(0) 
        
        self.__DIOCard.Register_Card(self.__CardId, self.__CardNumber)
        return1 = self.__DIOCard.DO_7300B_Config(self.__CardNumber, self.__PortWidth, self.__TrigSource,
                                       self.__WaitStatus, self.__Terminator, self.__O_Cntrl_Pol,
                                       self.__FifoThreshold)
        
        self.SampleRate = 20000000;
        # time interval used for calculating waveforms
        self.timeStep = 1/float(self.SampleRate)
        # mode A/B: 30, mode B/A: 15
        self.__clockBit = 15
        print 'DIO card configured'

    def changeSampleRate(self, SampleRateIn):
        self.SampleRate = SampleRateIn
        self.timeStep = 1/float(self.SampleRate)

    def writeWaveformPotentials(self, potentialsOut):
        
        # For (..) PCI-7300A (..) this argument must be set to 0.
        Port = ctypes.c_uint16(0) 
        value = ctypes.c_uint32(0)

        # three positive channels
        left = np.uint32(potentialsOut[1,:])
        middle = np.uint32(potentialsOut[3,:])
        right = np.uint32(potentialsOut[5,:])
    
        if self.__clockBit == 30:
            # port in order PA/PB configured
            self.buffer = np.zeros(np.size(left), dtype=np.uint32)
            
            # buffer of channels at each time step
            for i in np.arange(0, np.size(left)):

                # 10 bit for each channel
                self.buffer[i] = self.buffer[i] | left[i] | middle[i] << 10 | right[i] << 20
                # set clock bit alternatingly, starting high
                self.buffer[i] = self.buffer[i] | np.fmod(i+1,2) << self.__clockBit

        elif self.__clockBit == 15:
            # port in order PB/PA configured
            middleSplit = np.zeros(1, dtype=np.uint32)
            self.buffer = np.zeros(np.size(left), dtype=np.uint32)

            # buffer of channels at each time step
            mask = 2**32- 1
            for i in np.arange(0, np.size(left)):
                # set split channel PB/PA, rotation shift
                middleSplit = (middle[i] << 26 | middle[i] >> 6) & mask
                # 10 bit for each channel
                self.buffer[i] = self.buffer[i] | left[i] << 16 | middleSplit | right[i] << 4
                # set clock bit alternatingly, starting high
                self.buffer[i] = self.buffer[i] | np.fmod(i+1,2) << self.__clockBit
                
        # For (..) PCI-7300A (..) this argument must be set to 0.
        Port = ctypes.c_uint16(0) 
        # length of the buffer
        WriteCount = ctypes.c_uint32(np.size(left))
        Iterations = ctypes.c_uint16(1)
        # SYNCH_OP, ASYNCH_OP, sync when return after digital op completed
        SyncMode = ctypes.c_uint16(1)
        SampleRate = ctypes.c_double(self.SampleRate)
        # write data to ports with specified (internal) clock
        writeRet = self.__DIOCard.DO_ContWritePort(self.__CardNumber, Port, ctypes.c_void_p(self.buffer.ctypes.data), \
                                        WriteCount, Iterations, SampleRate, SyncMode)
        return writeRet

    def releaseCard(self):
        self.__DIOCard.Release_Card(self.__CardNumber)
        
if __name__ == "__main__":
    # some radio button for port configuration BA/AB
    DIOCard = DIOCardController()
    DIOCard.configureCard(False)
    print DIOCard.SampleRate
    print DIOCard.timeStep
    #DIOCard.changeSampleRate(10000000)
    #print DIOCard.timeStep
    #print DIOCard.SampleRate
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

