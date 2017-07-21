'''
Interface to NI USB-6212 analog I/O conroller
'''
import sys
import time
import ctypes

class AnalogOutController:
    '''interface to serial port wavemeter output'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            if sys.platform == 'darwin':
                raise OSError
            import PyDAQmx
            self.task = PyDAQmx.Task()
            minVal = -5.0
            maxVal = 5.0
            self.task.CreateAOVoltageChan("/Dev1/ao0", "", minVal, maxVal, PyDAQmx.DAQmx_Val_Volts, None)
            print 'Analog output NIDAQmx device driver found'
        except ImportError:
            print 'Device driver for NIDAQmx not present'

    def setVoltageOut(self, val):
        """Enable analog output of val(V) to channel AO0"""
        self.task.StartTask()
        # int32 DAQmxWriteAnalogScalarF64 (TaskHandle taskHandle, bool32 autoStart, \\
        # float64 timeout, float64 value, bool32 *reserved);
        # timeout = 0 attempt once
        err = self.task.WriteAnalogScalarF64(1, 0.0, val, None)
        if err != None:
            print "Error in analog writing operation occurred with code: {:s}".format(err)
        self.task.StopTask()

    def closeDevice(self):
        self.task.ClearTask()

if __name__ == '__main__':
    import time
    NIAO = AnalogOutController()
    NIAO.setVoltageOut(1.0)
    time.sleep(2)
    NIAO.setVoltageOut(2.0)
    time.sleep(2)
    NIAO.setVoltageOut(0.0)
    NIAO.closeDevice()
