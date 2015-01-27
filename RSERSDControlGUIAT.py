import time
from datetime import datetime
import gobject
import numpy
import os
import sys

from matplotlib.figure import Figure
import matplotlib
#matplotlib.use('GTKAgg') 
#from gtk import gdk
#from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas

from multiprocessing import Pipe, Process


# Add project root directory (enable symlink and trunk execution)
PROJECT_ROOT_DIRECTORY = os.path.abspath(os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0]))))
# add parent directory to search path for modules, for including the things in labcontrol without installing them. this is of course an ugly hack.
print PROJECT_ROOT_DIRECTORY
sys.path.append(os.path.join(os.path.split(PROJECT_ROOT_DIRECTORY)[0], 'RSERSDControl/labcontrol'))
print sys.path
from Instruments.LeCroyScopeController import LeCroyScopeController

try:
    import pygtk
    pygtk.require(2.0)
except:
    pass

try:
    import gtk
except:
    sys.exit(1)

def acquisitionLoop(pipe):
    scope = LeCroyScopeController()
    scope.initialize()
    scope.setScales()
    acquire = False
    while True:
        # process potential messages coming in
        if pipe.poll():
            msg = pipe.recv()
            print 'received message', msg
            if msg[0] == 'QUIT':
                break
            elif msg[0] == 'ACTIVATE':
                acquire = msg[1]
            else:
                print 'UNKNOWN COMMAND received!'
        
        if acquire:
            data = scope.armwaitread()
            pipe.send(data)
        else:
            time.sleep(.1)
        
class rydec(object):
    def __init__(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file('rydec.glade')
        signals = {'on_ionizerWindow_destroy' : gtk.main_quit,\
                             'on_btn_StartAcquisition_clicked' : self.on_btn_StartAcquisition_clicked}
        self.builder.connect_signals(signals)
        
        self.window = self.builder.get_object('rydecWindow')
        box = self.builder.get_object('box')
        
        fig = Figure(figsize=(5,4), dpi=100)
        self.axScope = fig.add_subplot(111)
        self.scopeCanvas = FigureCanvas(fig)
        box.pack_start(self.scopeCanvas)
        
        self.window.show_all()
        
        self.plotData = numpy.zeros(100)
        
        self.tagTimers = {}
        
        self.lastImage = None
        self.dataLabel = self.builder.get_object('txtDataLabel')
        self.dataLabel.set_text('unknown')
        
        self.active = False
        self.tagTimers = {}
        
        self.pipe, pipe = Pipe()
        self.acqLoop = Process(target=acquisitionLoop, args=(pipe, ))
        self.acqLoop.daemon = True
        self.acqLoop.start()
        
        # set the proper default directory for data:
        try: 
            os.chdir("D:\Data")
        except OSError:
            try:
                os.chdir("/tmp/")
            except OSError: 
                logger.error("Could not set data directory")
                
        try:
            today = datetime.now().strftime('%Y-%m-%d %a')
            if not os.path.exists(today):
                os.mkdir(today)
            os.chdir(today)
        except OSError: 
            logger.error("Could not create data directory")
        self.datadir = os.getcwd()

    
    def on_btn_StartAcquisition_clicked(self, widget):
        if self.active:
            self.pipe.send(['ACTIVATE', False])
            gobject.source_remove(self.tagTimers['ACQ'])
            del self.tagTimers['ACQ']
            widget.set_label('Start')
            self.active = False
        else:
            self.pipe.send(['ACTIVATE', True])
            self.tagTimers['ACQ'] = gobject.timeout_add(100, self.acquisitionTimer)
            widget.set_label('Stop')
            self.active = True
    
    def acquisitionTimer(self):
        if self.pipe.poll():
            self.axScope.clear()
            data = self.pipe.recv()
            self.axScope.plot(data)
            self.axScope.set_title('Scope trace signal', fontsize=12)
            self.axScope.set_xlabel(r'Time ($\mu$s)', fontsize=12)
            self.axScope.set_ylabel('Amplitude (V)', fontsize=12)
            self.axScope.axis([-0.02*len(data), len(data)*1.02, min(data)*1.2, max(data)*1.2])
            self.axScope.grid(True)
            #cursor = Cursor(self.scopeCanvas.ax, useblit=True, color='red', linewidth=2 )
            self.scopeCanvas.draw()
        return True
        
    def teardown(self):
        print 'tearing down everything'
        self.pipe.send(["QUIT"])
        if self.active:
            self.pipe.recv()
            self.pipe.close()
            self.acqLoop.join()


if __name__ == '__main__':
    wnd = rydec()
    try:
        gtk.main()
    except:
        print sys.exc_info()[0]
    finally:
        wnd.teardown()


