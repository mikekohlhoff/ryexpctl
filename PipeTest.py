import time
from datetime import datetime
import os
import sys
from multiprocessing import Pipe, Process
from PyQt4 import QtCore

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

class pipetest():
    def __init__(self):
        # connect to acq loop, parent connection, child connection
        self.timer = QtCore.QTimer();
        self.pipe, pipe = Pipe()
        self.acqLoop = Process(target=self.f, args=(pipe,))
        self.acqLoop.daemon = True
        self.acqLoop.start()
        self.pipe.send(['foobar'])
        
        if self.pipe.poll():
            out = self.pipe.recv()
            print out
        self.pipe.close()
        self.acqLoop.join(1)

    def f(self, conn):
        print 'foo'
        conn.send([42, None, 'hello'])
        conn.close()

if __name__ == '__main__':
    tp = pipetest()
    sys.exit()

##    
##    def acquisitionLoop(self,pipe):
##        pipe.send(['foobar'])
##        print 'foo'
##
##
##if __name__ == '__main__':
##    tp = pipetest()
