#!/usr/bin/env python3

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from math import ceil
# from scipy.signal import argrelextrema


def find_transit_valley(x, y):
    valleys = find_peaks(y*-1, distance=10)[0]
    thresh = np.percentile(y, 3)
    print("Threshold: {}".format(thresh))
    # There's a way to do this with list expressions; speedier that way
    good_valleys = []
    for idx in valleys:
        lum = y[idx]
        if lum < thresh:  # Dim enough to be a real valley
            good_valleys.append(idx)
    valley_x = x[good_valleys]
    valley_y = y[good_valleys]
    # The darkest 3% will be considered candidates for transition
    return valley_x, valley_y


def find_transit_period(vx, vy):
    # This gives us the time diff between each peak, some of which will be over
    # gaps in time where there is no data
    diffs = np.diff(valley_x)
    # We start knowing that at least every valley is when a transition occured
    valley_count = len(valley_x)
    last_trans = valley_x[-1]
    first_trans = valley_x[0]
    # Take a rough guess at the period.  This won't work if the period where
    # there are gaps are longer than the periods of obvservation.
    # TODO: Fix that.  That's gotta get fixed.
    P = (last_trans - first_trans) / (valley_count - 1)
    for d in diffs:
        if d > P:
            # If the time diff between valleys here is more than the average
            # period guess then we add in how many transitions should have
            # occured in this gap.
            vcount = ceil(d / P) - 1
            # print("Adding {} valleys due to gap".format(vcount))
            valley_count += vcount

    print("First transit: {}, Last transit (in sample): {}".format(first_trans,
                                                                   last_trans))
    print("Valleys found: {}".format(valley_count))
    # Now we get a real solid estimate of the period value
    P = (last_trans - first_trans) / (valley_count - 1)
    print("Period: {}".format(P))
    return P

def phase_shift(first_transit_time, origx, origy, P):
    origx -= valley_x[0]
    newx = []
    for i in origx:
        # Guarantee I'm doing something stupid here, not seeing it because I'm
        # working with the graph instead of thinking it through
        val = i - P/2
        val = val % P - P/2
        newx.append(val)
    # Sort both according to the X array
    newx, newy = zip(*sorted(zip(newx, origy)))
    return newx, newy

# Solid cases
_, allx, ally = np.loadtxt('data/KIC006922244.tbl', unpack=True, skiprows=3)
"""
_, allx, ally = np.loadtxt('data/KIC008359498.tbl', unpack=True, skiprows=3)
"""

# Not working yet.
"""
_, allx, ally = np.loadtxt('data/KIC002571238.tbl', unpack=True, skiprows=3)
_, allx, ally = np.loadtxt('data/KIC005881688.tbl', unpack=True, skiprows=3)
_, allx, ally = np.loadtxt('data/KIC007950644.tbl', unpack=True, skiprows=3)
_, allx, ally = np.loadtxt('data/KIC009631995.tbl', unpack=True, skiprows=3)
_, allx, ally = np.loadtxt('data/KIC010418224.tbl', unpack=True, skiprows=3)
_, allx, ally = np.loadtxt('data/KIC011853905.tbl', unpack=True, skiprows=3)
"""

valley_x, valley_y = find_transit_valley(allx, ally)
P = find_transit_period(valley_x, valley_y)
allx, ally = phase_shift(valley_x, allx, ally, P)

N = 551
meanx = np.convolve(allx, np.ones((N,))/N, mode='valid')[(N-1):]
meany = np.convolve(ally, np.ones((N,))/N, mode='valid')[(N-1):]

plt.scatter(allx, ally, s=1)
plt.plot(meanx, meany, "m")
# plt.scatter(valley_x, valley_y, marker='o', color='green', label='Valleys')
plt.xlabel("Julian Days")
plt.ylabel("Lc Intensity")
plt.show()
