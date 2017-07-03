'''
Controller for UHV Design stepper motor to step motor
for x-axis translation stage by '--distance/-d' {mm}
'''
import sys
import os
import time
from pyvisa.errors import VisaIOError
from pyvisa.resources import MessageBasedResource
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--distance', '-d', required=True, type=int)
args = parser.parse_args()

class MotorControllerXAxis:
    '''interface to stepper motor`'''
    def __init__(self):
        print '-----------------------------------------------------------------------------'
        try:
            import visa
            rm = visa.ResourceManager()
            self.__motor = rm.open_resource('ASRL5::INSTR', resource_pyclass=MessageBasedResource)
            self.__motor.timeout = 2000
            self.__motor.write_termination=u'\r'
            self.__motor.read_termination=u'\r'
        except ImportError:
            print 'Hardware not present, exit'
            sys.exit()
        except VisaIOError:
            print 'Hardware not responding, exit'
            sys.exit()

    def setMotor(self):
        # current
        self.__motor.write("2PC3")
        # limits
        self.__motor.write("2DL2")
        # microstepping
        self.__motor.write("2MR8")
        # acceleration
        self.__motor.write("2AC5")
        # n/a
        self.__motor.write("2DE5")
        # velocity
        self.__motor.write("2VE5")
        self.__motor.write("2PC")
        self.__motor.write("2DL")
        self.__motor.write("2AC")
        self.__motor.write("2DE")
        self.__motor.write("2VE")

    def moveDistance(self, distin=0):
        '''move stage by dist (mm)'''
        dist = 500000*distin
        print "Move motor by {:d}mm".format(distin)
        self.__motor.write("2DI{:d}".format(dist))
        self.__motor.write("2FL")

    def closeConnection(self):
        self.__motor.close()

if __name__ == '__main__':
    motor = MotorControllerXAxis()
    motor.setMotor()
    time.sleep(1)
    motor.moveDistance(args.distance)
    motor.closeConnection()
