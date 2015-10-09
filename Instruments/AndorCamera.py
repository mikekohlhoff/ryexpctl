# -*- Mode: Python; coding: utf-8; indent-tabs-mode: tab; tab-width: 2 -*-
### BEGIN LICENSE
# Copyright (C) 2010 <Atreju Tauschinsky> <Atreju.Tauschinsky@gmx.de>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

'''controller for andor cameras'''

import ctypes # dll interface
import numpy  # buffer allocation


# only for testing
#############################
from math import exp # only for test images!
import time # only for test images
#########################
import logging

# defines from atmcd32d.h
DRV_SUCCESS = 20002
DRV_IDLE = 20073
DRV_ACQUIRING = 20072


class AndorSimulator:
    '''simulator, used only if hardware not present'''
    #pylint: disable=C0321,C0111,R0913,C0103,W0613 
    def __init__(self): pass
    def Initialize(self, directory): pass
    def SetADChannel(self, channel): pass
    def SetHSSpeed(self, speedType, index): pass
    def SetVSSpeed(self, index): pass
    def GetVSSpeed(self, index, speed): pass
    def SetShutter(self, typ, mode, closingtime, openingtime): pass
    def SetTriggerMode(self, mode): pass
    def GetDetector(self, xpixels, ypixels):
        xpixels._obj.value = 666
        ypixels._obj.value = 333
    def SetPreAmpGain(self, index): pass
    def GetPreAmpGain(self, index, gain): pass
    def SetTemperature(self, temperature): pass
    def CoolerON(self): pass
    def CoolerOFF(self): pass
    def GetTemperature(self, temperature): pass
    def GetNumberNewImages(self, first, last):
        if time.clock()-self.acqStart > 2:
            last._obj.value = 1
        else:
            last._obj.value = 0
        first._obj.value = 1
    def GetStatus(self, status):
        if time.clock()-self.acqStart > 2:
            status._obj.value = DRV_IDLE
    def GetOldestImage(self, arr, size): pass
    def GetMostRecentImage16(self, arr, size):
        buff = numpy.ndarray(size.value, dtype=numpy.uint16, buffer=(ctypes.c_uint16*size.value).from_address(arr))
        buff[:] = numpy.random.randint(0, 100, size.value)
    def GetMostRecentImage(self, arr, size): pass
    def SetReadMode(self, mode): pass
    def SetImage(self, hBin, vBin, hStart, hEnd, vStart, vEnd):
        self.size_x = hEnd.value - hStart.value
        self.size_y = vEnd.value - vStart.value
    def SetAcquisitionMode(self, mode): pass
    def SetNumberAccumulations(self, number): pass
    def SetNumberKinetics(self, number): pass
    def SetExposureTime(self, exposureTime): pass
    def StartAcquisition(self):
        self.acqStart = time.clock()
    def Shutdown(self): pass
    def GetNumberVSSpeeds(self, speeds): pass
    def SetEMCCDGain(self, gain): pass
    def GetEMCCDGain(self, gain): pass
    def WaitForAcquisition(self): time.sleep(2)

class AndorController:
    '''interface to andor camera'''
    def __init__(self):
        try:
            self.__andor = ctypes.windll.atmcd32d
        except AttributeError:
            print "WARN: can't load Andor driver, using simulator"
            self.__andor = AndorSimulator()

    def initialize(self, trigmode, exp):
        '''initialize camera'''
        print self.__andor.Initialize("")
        self.__andor.SetShutter(ctypes.c_int(0), ctypes.c_int(0), ctypes.c_int(95), ctypes.c_int(0))
        px = ctypes.c_int(0)
        py = ctypes.c_int(0)
        self.__andor.GetDetector(ctypes.byref(px), ctypes.byref(py))
        self.size_x, self.size_y = px.value, py.value
        
        self.__andor.SetImage(ctypes.c_int(1), ctypes.c_int(1), ctypes.c_int(1), px, ctypes.c_int(1), py)
        # mode 4: Image
        self.__andor.SetReadMode(ctypes.c_int(4))
        nspeeds = ctypes.c_int(0)
        self.__andor.GetNumberVSSpeeds(ctypes.byref(nspeeds))
        self.__andor.SetVSSpeed(ctypes.c_int(nspeeds.value - 1))
        # mode 0: internal, 1: ext, 6: ext start
        print self.__andor.SetTriggerMode(ctypes.c_int(trigmode))
        self.__andor.SetHSSpeed(0, 0)
        #exposure time in seconds
        print self.setExposure(exp)
        #self.__andor.GetAcquisitionTimings # might not be necessary?
        print self.__andor.SetAcquisitionMode(ctypes.c_int(2))
        # mode 1: single scan, mode 2: accumulate
        print self.__andor.SetNumberAccumulations(ctypes.c_int(1))

        
    def setExposure(self, exp):
        self.__andor.SetExposureTime(ctypes.c_float(exp))
        
    def setTriggerMode(self, mode):
        print self.__andor.SetTriggerMode(ctypes.c_int(mode))
        
    def startAcquisition(self):
        '''start acquisition'''
        temp = ctypes.c_int(0)
        self.__andor.GetTemperature(ctypes.byref(temp))
        print 'current camera temperature: ', temp.value
        gain = ctypes.c_int(10)
        self.__andor.SetEMCCDGain(gain)
        gain = ctypes.c_int(0)
        self.__andor.GetEMCCDGain(ctypes.byref(gain))
        self.__andor.StartAcquisition()
        return [temp.value, gain]
    
    def shutdown(self):
        '''turn off camera'''
        self.__andor.Shutdown()
    
    def waitForImage(self):
        self.__andor.WaitForAcquisition()
    
    def getImage(self):
        '''retrieve oldest image available'''
        # TODO: Size is wrong if Binning is != 1
        img = numpy.zeros((self.size_y, self.size_x), dtype=numpy.uint16)
        self.__andor.GetMostRecentImage16(img.ctypes.data, ctypes.c_ulong(self.size_x*self.size_y))
        return img

    def getNumberAvailableImages(self):
        '''return number of images available on camera'''
        status = ctypes.c_int(0)
        self.__andor.GetStatus(ctypes.byref(status))
        if status.value != DRV_IDLE:
            return 0
        first = ctypes.c_long(0)
        last = ctypes.c_long(0)
        self.__andor.GetNumberNewImages(ctypes.byref(first), ctypes.byref(last))
        return last.value - first.value + 1
