#!/usr/bin/env python3

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from math import ceil
# from scipy.signal import argrelextrema


_, allx, ally = np.loadtxt('data/KIC006922244.tbl', unpack=True, skiprows=3)

x = allx
y = ally

valleys = find_peaks(y*-1, distance=10)[0]
# OK, I can't get SciPy to give me what I want to I'm going to manually
# trim off anything above 'thresh' luminiance
thresh = -0.006
print("Threshold: {}".format(thresh))
good_valleys = []
for idx in valleys:
    lum = y[idx]
    if lum < thresh:  # Dim enough to be a real valley
        good_valleys.append(idx)

valley_x = x[good_valleys]
valley_y = y[good_valleys]

# This gives us the time diff between each peak, some of which will be over
# gaps in time where there is no data
diffs = np.diff(valley_x)
# We start knowing that at least every valley is when a transition occured
valley_count = len(valley_x)
last_trans = valley_x[-1]
first_trans = valley_x[0]
# Take a rough guess at the period.  This won't work if the period where there
# are gaps are longer than the periods of obvservation.
# TODO: Fix that.  That's gotta get fixed.
P = (last_trans - first_trans) / (valley_count - 1)

for d in diffs:
    if d > P:
        # If the time diff between valleys here is more than the average period
        # guess then we add in how many transitions should have occured in
        # this gap.
        vcount = ceil(d / P) - 1
        # print("Adding {} valleys due to gap".format(vcount))
        valley_count += vcount

print("First transit: {}, Last transit (in sample): {}".format(first_trans,
                                                               last_trans))
print("Valleys found: {}".format(valley_count))
# Now we get a real solid estimate of the period value
P = (last_trans - first_trans) / (valley_count - 1)
print("Period: {}".format(P))

time_zero = valley_x[0]
new_valley_x = []
for i in allx:
    # Now shift the data so the first transit is at time 0.000
    val = i - time_zero - P/2
    # And fold it
    val = val % P
    new_valley_x.append(val)
allx = new_valley_x

plt.scatter(allx, ally, s=1)
# plt.scatter(valley_x, valley_y, marker='o', color='green', label='Valleys')
plt.xlabel("Julian Days")
plt.ylabel("Lc Intensity")
plt.show()
