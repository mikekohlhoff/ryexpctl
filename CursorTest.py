import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.widgets import RectangleSelector
from matplotlib.widgets import MultiCursor
import numpy as np

fig, ax = plt.subplots()
fig.subplots_adjust(bottom=0.2, left=0.1)

t = np.linspace(0, 10, 1000)
line, = plt.plot(t, np.sin(t), lw=2)

def on_change(val):
    line.set_ydata(np.sin(t - val))

slider_ax = plt.axes([0.1, 0.1, 0.8, 0.02])
slider = Slider(slider_ax, "Offset", -5, 5, valinit=0, color='#AAAAAA')
slider.on_changed(on_change)

fig, ax = plt.subplots()
x = np.random.normal(size=1000)
y = np.random.normal(size=1000)
c = np.zeros((1000, 3))
c[:, 2] = 1  # set to blue
points = ax.scatter(x, y, s=20, c=c)

def selector_callback(eclick, erelease):
    x1, y1 = eclick.xdata, eclick.ydata
    x2, y2 = erelease.xdata, erelease.ydata
    global c
    c[(x >= min(x1, x2)) & (x <= max(x1, x2))
      & (y >= min(y1, y2)) & (y <= max(y1, y2))] = [1, 0, 0]
    points.set_facecolors(c)
    fig.canvas.draw()
    
    
selector = RectangleSelector(ax, selector_callback,
                             drawtype='box', useblit=True,
                             button=[1,3], # don't use middle button
                             minspanx=5, minspany=5,
                             spancoords='pixels')

fig, ax = plt.subplots(2)

x, y, z = np.random.normal(0, 1, (3, 1000))

ax[0].scatter(x, y)
ax[1].scatter(x, z)

multi = MultiCursor(fig.canvas, ax, useblit=True, color='gray', lw=1)

plt.show()
