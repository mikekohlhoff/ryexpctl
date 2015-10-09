from AndorCamera import AndorController
import time
from datetime import datetime
import gobject
import numpy

import Image

import csv

import os

from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
import matplotlib.pyplot as plt

from multiprocessing import Pipe, Process

import sys
try:
    import pygtk
    pygtk.require(2.0)
except:
    pass

try:
    import gtk
except:
    sys.exit(1)


cmap_lv = numpy.zeros(shape=(256, 4), dtype=numpy.uint8)
cmap_lv[0:32, 0] = numpy.linspace(192, 0, 32)
cmap_lv[128:160, 0] = numpy.linspace(0, 255, 32)
cmap_lv[160:256, 0] = 255
cmap_lv[64:96, 1] = numpy.linspace(0, 192, 32)
cmap_lv[96:128, 1] = 192
cmap_lv[128:160, 1] = numpy.linspace(192, 255, 32)
cmap_lv[160:192, 1] = numpy.linspace(255, 128, 32)
cmap_lv[192:224, 1] = numpy.linspace(127, 64, 32)
cmap_lv[224:256, 1] = numpy.linspace(64, 255, 32)
cmap_lv[0:32, 2] = numpy.linspace(192, 0, 32)
cmap_lv[32:64, 2] = numpy.linspace(0, 192, 32)
cmap_lv[64:96, 2] = 192
cmap_lv[96:128, 2] = numpy.linspace(192, 0, 32)
cmap_lv[192:224, 2] = numpy.linspace(0, 64, 32)
cmap_lv[224:256, 2] = numpy.linspace(64, 255, 32)

cmap = cmap_lv

    
def acquisitionLoop(pipe):
    acquire = False
    cam = AndorController()
    cam.initialize()
    while True:
        # process potential messages coming in
        if pipe.poll():
            msg = pipe.recv()
            print 'received message', msg
            if msg[0] == 'QUIT':
                break
            elif msg[0] == 'ACTIVATE':
                acquire = msg[1]
            elif msg[0] == 'EXPOSURE':
                cam.setExposure(msg[1])
            else:
                print 'UNKNOWN COMMAND received!'
        
        if acquire:
            cam.startAcquisition()
            cam.waitForImage()
            img = cam.getImage()
            pipe.send(img)
        else:
            time.sleep(.1)
    #cam.shutdown()
        
def savePGM(filename, data):
    '''save image data as 16 bit PGM file'''
    with open(filename, 'wb') as f:
        f.write("%s\n" % ("P5")) 
        f.write("%d %d\n" % (data.shape[1], data.shape[0])) 
        f.write("%d\n" % (65535)) 
        f.write(data.byteswap()) # matlab expects big-endian for 16 bit PGM files??
        
        
class ionizer(object):
    def __init__(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file('ionizer.glade')
        signals = {'on_ionizerWindow_destroy' : gtk.main_quit,\
                             'on_btn_StartAcquisition_clicked' : self.on_btn_StartAcquisition_clicked,\
                             'on_btnSave_clicked' : self.on_save,\
                             'on_adjExposure_value_changed' : lambda w: self.pipe.send(['EXPOSURE', w.get_value()])}
        self.builder.connect_signals(signals)
        self.window = self.builder.get_object('ionizerWindow')
        box = self.builder.get_object('box')
        
        self.fig = Figure(figsize=(5,4), dpi=100)
        self.axCam = self.fig.add_subplot(111)
        self.Camcanvas = FigureCanvas(self.fig)
        box.pack_start(self.Camcanvas)
        
        self.window.show_all()
        
        
        self.tagTimers = {}
        
        self.lastImage = None
        self.dataLabel = self.builder.get_object('txtDataLabel')
        self.dataLabel.set_text('unknown')
        
        self.active = False
        self.isControlling = False
        
        
        self.pipe, pipe = Pipe()
        self.acqLoop = Process(target=acquisitionLoop, args=(pipe, ))
        self.acqLoop.daemon = True
        self.acqLoop.start()
        
        self.cmap = plt.cm.bone#bone#afmhot#coolwarm
        # set the proper default directory for data:
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
        else:#
            self.pipe.send(['ACTIVATE', True])
            self.tagTimers['ACQ'] = gobject.timeout_add(50, self.acquisitionTimer)
            widget.set_label('Stop')
            self.active = True
    
    def acquisitionTimer(self):
        if self.pipe.poll():
            self.axCam.clear()
            self.lastImage = self.pipe.recv()
            self.axCam.imshow(self.lastImage, cmap = self.cmap)#, vmin=450, vmax=650)
            print self.lastImage.min()
            print self.lastImage.max()
            self.Camcanvas.draw()
        return True
        
        
    def on_save(self, btn):
        prefix = datetime.now().strftime('%H%M%S-') + self.dataLabel.get_text()
        print 'saving to', prefix
        self.fig.savefig(prefix + '.png')
        numpy.save(prefix, self.lastImage)
#       if self.lastImage is not None:
#           savePGM(prefix + '.pgm', self.lastImage)
#           Image.fromarray(cmap[(1.*self.lastImage/self.lastImage.max()*255).astype(int)]).convert('RGB').save(prefix + '.jpg')
        
    def teardown(self):
        print 'tearing down everything'
        for t in self.tagTimers:
            gobject.source_remove(self.tagTimers[t])
        self.pipe.send(["QUIT"])
        if self.active:
            self.pipe.recv()
            self.pipe.close()
            self.acqLoop.join()


if __name__ == '__main__':
    wnd = ionizer()
    try:
        gtk.main()
    except:
        print sys.exc_info()[0]
    finally:
        wnd.teardown()


