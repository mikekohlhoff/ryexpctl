import time
from datetime import datetime
import os
import sys
from multiprocessing import Pipe, Process
from PyQt4 import QtCore, QtGui

##class pipetest():
##    def __init__(self):
##        self.timer = QtCore.QTimer()
##        self.parent_conn, child_conn = Pipe()
##        self.p = Process(target=self.f, args=(child_conn,))
##        self.p.daemon = True
##        self.p.start()
##        print self.parent_conn.recv()   # prints "[42, None, 'hello']"
##        self.p.join()
##
##    def f(self, conn):
##        conn.send([42, None, 'hello'])
##        conn.close()
#timer = QtCore.QTimer();
#def startTimer():
#    timer.start()


def f(self, conn):
    print 'foo'
    conn.send([42, None, 'hello'])
    conn.close()
    conn.join()

#class pipetest(QtCore.QObject):
class pipetest():
    def __init__(self,parent=None):
        #super(pipetest).__init__(parent)
        self.mainTimer = QtCore.QTimer(parent=None)
        self.mainTimer.start()
        self.pipe, pipe = Pipe()
        self.acqLoop = Process(target=f, args=(pipe,))
        self.acqLoop.daemon = True
        self.acqLoop.start()
        self.pipe.send(['foobar'])
        #timer.singleShot(2000,self.acLoop)
        
    def acLoop(self):
        if self.pipe.poll():
            out = self.pipe.recv()
            print out
        self.pipe.close()
        

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    app.exec_()
    tp = pipetest()
    #sys.exit()

##    
##    def acquisitionLoop(self,pipe):
##        pipe.send(['foobar'])
##        print 'foo'
##
##
##if __name__ == '__main__':
##    tp = pipetest()
