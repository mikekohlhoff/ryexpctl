from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import sys

# UI related
from PyQt4 import QtCore, QtGui, uic
ui_form = uic.loadUiType("alfonso.ui")[0]


class Alfonso(QtGui.QMainWindow, ui_form):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.show()
        self.i = 0
        # define slots and signals: widgetobj.signal.connect(slot)
        self.button1.clicked.connect(self.buttonClicked)
        self.listView.doubleClicked.connect(self.buttonClickedTwice)
        self.postdoc.clicked.connect(self.checkBoxClicked)
        self.scopeThread.dataReady.connect(dataAcq)
        
    def dataAcq(self):
        # data display
      
    def buttonClicked(self):
        self.i += 1
        self.txtout.setText('Hello World ' + str(self.i))

    def buttonClickedTwice(self):
        self.i += 2
        self.txtout.setText('Hello World ' + str(self.i))
    
    def checkBoxClicked(self):
        reply = QtGui.QMessageBox.question(self, 'RSE Control',
                "Shut down camera control?", QtGui.QMessageBox.Yes | 
                QtGui.QMessageBox.Cancel, QtGui.QMessageBox.Cancel)  
        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
    
class scopeThread(QtCore.QThread):
    init
    
    dataReady = signal
    def run
    while True:
        data = scope.waitread()
        dataReady.emit
            
if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    myapp = Alfonso()
    app.exec_()