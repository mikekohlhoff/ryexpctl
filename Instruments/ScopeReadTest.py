''' Test single shot read out from scope'''

from time import clock

from ScopeController import ScopeController

from array import array
from matplotlib import pyplot as plt
import random
import time

sc = ScopeController()
sc.initialize()
sc.setSweeps(1)
sc.setScales()
#sc.armScope()


#t1 = clock()

#for i in range(50):
#    data = sc.armwaitread()
    
#t2 = clock() - t1
#print 'time for 50 traces:', t2
#print 'frequency: ', 50./t2

data = sc.armwaitread()
plt.plot(data)
plt.show()

sc.dispOff
print 'DISP OFF'
#time.sleep(20)
sc.dispOn()
print 'DISP ON'
