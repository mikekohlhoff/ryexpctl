# -*- coding: utf-8 -*-
import sys
from PyQt4 import QtCore, QtGui, uic
from PyQt4.QtCore import Qt
ui_form = uic.loadUiType("rsdgui.ui")[0]
import time

# very testable class (hint: you can use mock.Mock for the signals)
class Worker(QtCore.QObject):
    finished = QtCore.pyqtSignal()
    dataReady = QtCore.pyqtSignal(list, dict)

    @QtCore.pyqtSlot()
    def processA(self):
        print "Worker.processA()"
        self.finished.emit()

    @QtCore.pyqtSlot(str, list, list)
    def processB(self, foo, bar=None, baz=None):
        print "Worker.processB()"
        for thing in bar:
            # lots of processing...
            self.dataReady.emit(['dummy', 'data'], {'dummy': ['data']})
        self.finished.emit()


def onDataReady(aList, aDict):
    print 'onDataReady'
    print repr(aList)
    print repr(aDict)

class MainCtl(QtGui.QMainWindow, ui_form):
    #app = QtGui.QApplication(sys.argv)
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.show()
        self.thread = QtCore.QThread()  # no parent!
        self.obj = Worker()  # no parent!
        self.obj.dataReady.connect(onDataReady)

        self.obj.moveToThread(self.thread)

# if you want the thread to stop after the worker is done
# you can always call thread.start() again later
        self.obj.finished.connect(self.thread.quit)
       # self.obj.finished.connect(self.thread.deleteLater)
        self.obj.finished.connect(self.obj.deleteLater)
        self.thread.finished.connect(self.obj.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
# one way to do it is to start processing as soon as the thread starts
# this is okay in some cases... but makes it harder to send data to
# the worker object from the main gui thread.  As you can see I'm calling
# processA() which takes no arguments
        self.thread.started.connect(self.obj.processA)
        #self.thread.finished.connect(app.exit)

        self.thread.start()

# another way to do it, which is a bit fancier, allows you to talk back and
# forth with the object in a thread safe way by communicating through signals
# and slots (now that the thread is running I can start calling methods on
# the worker object)
        QtCore.QMetaObject.invokeMethod(self.obj, 'processB', Qt.QueuedConnection,
                                QtCore.Q_ARG(str, "Hello World!"),
                                QtCore.Q_ARG(list, ["args", 0, 1]),
                                QtCore.Q_ARG(list, []))
        
        time.sleep(3)
        self.obj = Worker()  # no parent!
        self.thread = QtCore.QThread()  # no parent!
        self.obj.moveToThread(self.thread)
        self.obj.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.obj.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.obj.finished.connect(self.obj.deleteLater)
        self.thread.started.connect(self.obj.processA)
        self.thread.start()
# that looks a bit scary, but its a totally ok thing to do in Qt,
# we're simply using the system that Signals and Slots are built on top of,
# the QMetaObject, to make it act like we safely emitted a signal for
# the worker thread to pick up when its event loop resumes (so if its doing
# a bunch of work you can call this method 10 times and it will just queue
# up the calls.  Note: PyQt > 4.6 will not allow you to pass in a None
# instead of an empty list, it has stricter type checking
        app.exit

if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    myapp = MainCtl()
    app.exec_()
  #  sys.exit(app.exec_())




