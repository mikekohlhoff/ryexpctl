import sys, time
from PyQt4 import QtCore, QtGui

class WorkThread(QtCore.QThread):
 def __init__(self):
  QtCore.QThread.__init__(self)

 # override
 def __del__(self):
  self.wait()
 
 def run(self):
#  for i in range(6):
  while self.runBool:
   time.sleep(0.5) # artificial time delay
   self.emit( QtCore.SIGNAL('update(QString)'), "from work thread ")
  return

class MyApp(QtGui.QWidget):
 def __init__(self, parent=None):
  QtGui.QWidget.__init__(self, parent)
 
  self.setGeometry(300, 300, 280, 600)
  self.setWindowTitle('threads')
 
  self.layout = QtGui.QVBoxLayout(self)
 
  self.testButton = QtGui.QPushButton("test")
  self.connect(self.testButton, QtCore.SIGNAL("released()"), self.test)
  self.listwidget = QtGui.QListWidget(self)
 
  self.layout.addWidget(self.testButton)
  self.layout.addWidget(self.listwidget)
 
 def add(self, text):
  """ Add item to list widget """
  print "Add: " + text
  self.listwidget.addItem(text)
  self.listwidget.sortItems()
 
 def addBatch(self,text="test",iters=6,delay=0.5):
  """ Add several items to list widget """
  for i in range(iters):
   time.sleep(delay) # artificial time delay
   self.add(text+" "+str(i))
 
 def test(self):
  self.listwidget.clear()
  # adding entries just from main application: locks ui
  #self.addBatch("_non_thread",iters=6,delay=0.5)

  # adding by emitting signal in different thread
  self.workThread = WorkThread()
  self.workThread.runBool = True
  self.connect( self.workThread, QtCore.SIGNAL("update(QString)"), self.add )
  self.workThread.start()
  time.sleep(3)
  self.workThread.runBool = False
  
# run
app = QtGui.QApplication(sys.argv)
test = MyApp()
test.show()
app.exec_()
  
