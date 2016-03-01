# -*- coding: utf8 -*-
"""
Functions for time varying potentials for a number of electrodes for PCB RSD. \n\
Output for 10bit D/A channel.
"""

from numpy import *
import textwrap
import matplotlib.pyplot as plt
import math

# Build ELECTRODE POTENTIALS piece-wise for incoupling, chirp, outcoupling ported form Matlab 
# Oscillation frequency omega building phase, constant (inc/outc) or non-constant 
# over time (chirp); t0=0, t1=incplTime, t2=incplTime+decelTime, t3=relative time(end)-outcplTime, 
# t4=time(end)
# timeInRev in order to ensure that position of targeted minimum is always at same position after set
# incoupling time
# chirp chosen to end at fixed position before field minima diverges

class WaveformPotentials23Elec:
    
    """
    Generate (chirped) waveform potentials for decelerator.
    Potentials need to be generated before plotted.
    """

    def generate(self,timeStep,vInit,vFinal,incplTime,outcplTime,maxAmp,decelDist,elecSelect):
        
        # Distance between field minima, 3*center-to-center spacing of electrodes
        dmin = 3E-3
        # to be transposed, chose minimum position depending on which electrode pair firt Umax
        if '(1,4)' in elecSelect:
            phaseOffset = array([[0], [2], [1], [0], [2], [1]])*(2*pi/3.0)
        elif '(3,6)' in elecSelect:
            phaseOffset = array([[2], [1], [0], [2], [1], [0]])*(2*pi/3.0)
        elif '(2,5)' in elecSelect:
            phaseOffset = array([[1], [0], [2], [1], [0], [2]])*(2*pi/3.0)
        
        incplTime = incplTime*1E-6
        outcplTime = outcplTime*1E-6
        decelDist = decelDist*1E-3
        # 23 electrodes with 0.5mm width and 0.5mm apart w/o margins
        chipLength = (23.5)*1E-3

        # Check available deceleration path length over chip
        distanceTotal = vInit*incplTime + vFinal*outcplTime + decelDist
        # Time passed during a-/decceleration for given length decelDist
        decelTime = 2*decelDist/(vInit+vFinal)
        incplTime = floor(incplTime/timeStep)*timeStep
        outcplTime = floor(outcplTime/timeStep)*timeStep
        decelTime = floor(decelTime/timeStep)*timeStep
        # index time with integers, better comparison with .m code
        timeTotal = floor((decelTime + outcplTime)/timeStep)
        timeTotalInt = floor((decelTime + outcplTime)/timeStep)
        time = arange(0, timeTotalInt+1, 1)*timeStep

        if distanceTotal > chipLength: pass

        # 1. INCOUPLING, linear increase in amplitude, constant omega
        # compare in ns to avoid rounding errors
        timeInRev = time[time <= incplTime]
        timeIn = -flipud(time[time <= incplTime])
        omegaConst = 2*pi*vInit/dmin
        phaseIn = omegaConst*timeIn
        if incplTime != 0:
            ampIn = maxAmp*(tile(timeInRev, (6,1))/incplTime)
            ampIn[ampIn > maxAmp] = 0
        else:
            ampIn = array([[],[],[],[],[],[]])
        phaseIn = tile(phaseIn, (6,1)) + tile(phaseOffset, (1,len(timeIn)))
        newPotIn = ampIn*tile(array([[-1],[1],[-1],[1],[-1],[1]]), (1,len(timeIn)))*(cos(phaseIn)+1)
        
        # 2. electrode potentials with LINEAR CHIRP
        # decelTime + incpltime = t2, t=(ti-t1)
        timeChirp = time[time < decelTime] + timeStep
        freqSlope = (pi/(2*decelDist*dmin)*(vFinal**2-vInit**2))
        phaseChirp = (freqSlope*(timeChirp) + 2*pi*vInit/dmin)*(timeChirp)
        chirpOffset = 2*pi/dmin*vInit*(incplTime)
        # keep minimum at position for elec 1/4 = Umax (instead of phase=phaseChirp+chirpOffset)
        phase = phaseChirp
        phase = tile(phase, (6,1)) + tile(phaseOffset, (1,len(timeChirp)))
        newPotChirp = maxAmp*tile(array([[-1],[1],[-1],[1],[-1],[1]]), (1,len(timeChirp)))*(cos(phase)+1)
        
        # 3.A CONSTANT frequency after chirp completed until potentials ramp to zero in outcoupling
        # don't account for incoupling time
        timePostChirp = time[time < (time[-1] - decelTime)] + timeStep
        postOffset = 2*pi/dmin*(vInit*(decelTime) + \
                    (vFinal**2-vInit**2)/(4*decelDist)*(decelTime)**2)
        phasePostChirp = 2*pi/dmin*vFinal*timePostChirp + postOffset
        phasePostChirp = tile(phasePostChirp, (6,1)) + tile(phaseOffset, (1,len(timePostChirp)))
        newPotPostChirp = maxAmp*tile([[-1],[1],[-1],[1],[-1],[1]], (1,len(timePostChirp)))*(cos(phasePostChirp)+1)

        # 3.B OUTCOUPLING, linear decrease in amplitude for omega1
        timeOut = timePostChirp + decelTime
        ampOut = tile(time[-1] + 1*timeStep -  timeOut, (6,1))/outcplTime
        ampOut[ampOut > 1] = 1
        newPotPostChirp = newPotPostChirp*ampOut

        self.maxAmp = maxAmp
        self.incplTime = incplTime*1E6
        self.outcplTime = outcplTime*1E6
        self.decelTime = decelTime*1E6
        
        # concatenate intervals and round to integers
        # set first and last element to zero
        zeroel = zeros((6,1))
        potentialsOut = around(hstack((newPotIn, newPotChirp, newPotPostChirp, zeroel)))
        # for clock bit in wf generator circuitry to have even number of samples
        if max(shape(potentialsOut))%2==1:
            potentialsOut = around(hstack((potentialsOut, zeroel)))        
            
        self.plotTime = 1E6*timeStep*arange(0,max(shape(potentialsOut)),1)
        # if any entry is NaN replace with 0
        self.potentialsOut = nan_to_num(potentialsOut)  
        
        mes = '{0:.2f}'.format(self.plotTime[-1])
        return mes
        
    def plot(self):
        if hasattr(self, 'plotTime'):
            argX = self.plotTime
            argY = self.potentialsOut
            plt.plot(1)
            # only plot positive channels
            plt.plot(argX, argY[1,:], 'r', label="1", linewidth=1.5)
            plt.plot(argX, argY[3,:], 'g', label="2", linewidth=1.5)
            plt.plot(argX, argY[5,:], 'b', label="3", linewidth=1.5)
            plt.axis([-2, self.plotTime[-1]+0.5, -10, self.maxAmp*2+10])
            plt.grid(True)
            plt.title("Calculated potential waveforms")
            plt.xlabel("Time ($\mu$s)")
            plt.legend(bbox_to_anchor=(1.02, 1), loc=2, borderpad=none, borderaxespad=0., fontsize=8)
            #plt.legend(loc="upper right")
            # mark different phases in potential generation 
            plt.plot([self.incplTime,self.incplTime],[10,(self.maxAmp*(-2)-10)], 'k--', linewidth=1)
            plt.plot([self.incplTime+self.decelTime,self.incplTime+self.decelTime],[-1,self.maxAmp*2+1], \
            'k--', linewidth=1)
            plt.ion()
            plt.show(block=True)
        else:
            print "No potentials generated"
        
if __name__ == '__main__':
    wfpot = WaveformPotentials21Elec()
    vFinal = 700
    outTime = 2.2*1E-3/vFinal*1E6
    #outTime = 3
    timestep = 1./20E6
    #timestep = 10E-8
    wfpot.generate(timestep,700,vFinal,0,outTime,1023/2,19.1)
    #print shape(wfpot.potentialsOut)
    wfpot.plot()

