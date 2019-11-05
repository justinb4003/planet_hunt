#!/usr/bin/env python3

import numpy as np
import pandas as pd
import sqlalchemy as sa
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from math import ceil
# from scipy.signal import argrelextrema

# Sloppy global DB connection stuff here.
sa_engine = sa.create_engine(
                'postgresql+psycopg2://kuser:kpass@localhost/kepler')
metadata = sa.MetaData()


# DEAD CODE: Original filename version left intact for a bit
def get_answer_filename():
    return 'kepler_accepted_results.csv'


# DEAD CODE: Original filename version left intact for a bit
def get_datafile_filename(kepid):
    kepstr = '{:09d}'.format(kepid)
    return 'data/KIC{}.tbl'.format(kepstr)


def get_sa_table(tblname):
    tbl = sa.Table(tblname, metadata, autoload=True, autoload_with=sa_engine)
    return tbl


def get_observation_tbl():
    return get_sa_table('observation')


def get_result_tbl():
    return get_sa_table('nasa_result')


# PROBLEM:  Having to futz with this percentile between runs
# .... obviously there's a better stats method to go about narrowing
# this down.
def find_transit_valley(x, y, percentile):
    valleys = find_peaks(y*-1, distance=10)[0]

    valley_x = []
    valley_y = []
    if len(valleys) > 1:
        thresh = np.percentile(y, percentile)
        print("Threshold: {}".format(thresh))
        # There's a way to do this with list expressions; speedier that way
        good_valleys = []
        for idx in valleys:
            lum = y[idx]
            if lum < thresh:  # Dim enough to be a real valley
                good_valleys.append(idx)
        valley_x = x[good_valleys]
        valley_y = y[good_valleys]
    else:
        # Should pick up othe techniques here. At least log when we only
        # get one.  That should be a fun exercise.
        print("Only found {} valleys in data. "
              "Cannot proceed.".format(len(valleys)))
        pass

    return valley_x, valley_y


def strip_outliers(lst, m=2):
    d = np.abs(lst - np.median(lst))
    mdev = np.median(d)
    s = d / (mdev if mdev else 1.0)
    return lst[s < m]


def find_transit_period(vx, vy):
    # This gives us the time diff between each peak, some of which will be over
    # gaps in time where there is no data
    diffs = np.diff(vx)
    # We start knowing that at least every valley is when a transition occured
    valley_count = len(vx)
    last_trans = vx[-1]
    first_trans = vx[0]
    # Take a rough guess at the period.  This won't work if the period where
    # there are gaps are longer than the periods of obvservation.
    # TODO: Fix that.  That's gotta get fixed.
    P = (last_trans - first_trans) / (valley_count - 1)
    print("First stab at P: {}".format(P))
    """
    diffs = strip_outliers(diffs)
    P = np.mean(diffs)
    print("Second stab at P: {}".format(P))
    """

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


# Shift every X back in time until it's relative position to transition always
# puts peak transition at time = 0.000
def phase_shift(first_transit_time, origx, origy, P):
    origx -= first_transit_time
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


def load_kepid_from_file(kepid):
    _, allx, ally = np.loadtxt(get_datafile_filename(kepid),
                               unpack=True,
                               skiprows=3)
    return allx, ally


def load_kepid_from_db(kepid):
    ot = get_observation_tbl()
    where = ot.c.kepler_id == kepid
    oq = sa.select([ot]).where(where)
    with sa_engine.connect() as cur:
        rs = cur.execute(oq).fetchall()

    # Reformat data in a very non-python way
    allx = []
    ally = []
    for row in rs:
        allx.append(row.time_val)
        ally.append(row.lc_init)
    print(len(allx), len(ally))
    return allx, ally


def calculate_result(kepid, percentile, show_valley=False, show_result=False):
    """
    kepid: Kepler Object ID (star) that we're looking at.
    percentile: Kind of a magic number at this point, generally 0.5-3%
                is where we make the threshold for a valley being legit
    TODO: This only looks for a single object, the largest one.
    """
    allx, ally = load_kepid_from_db(kepid)
    valley_x, valley_y = find_transit_valley(allx, ally, percentile)

    if show_valley:  # A debbuging graph showing where we think transits are
        plt.scatter(allx, ally, s=1)
        plt.scatter(valley_x, valley_y, s=3)
        plt.xlabel("Julian Days")
        plt.ylabel("Lc Intensity")
        plt.show()

    if len(valley_x) > 0:
        P = find_transit_period(valley_x, valley_y)
        allx, ally = phase_shift(valley_x[0], allx, ally, P)
    else:
        print("Not attempting phase shift, no period detected.")
        P = -1  # Bogus return value

    # Take a running mean of N size for each list
    N = 551  # <-- magic number found via fiddling
    meanx = np.convolve(allx, np.ones((N,))/N, mode='valid')[(N-1):]
    meany = np.convolve(ally, np.ones((N,))/N, mode='valid')[(N-1):]

    # If the graph is a scatter showing a nice U with a magenta line cutting
    # right through it you've got a planet.
    if show_result:
        plt.scatter(allx, ally, s=1)
        plt.plot(meanx, meany, "m")
        plt.xlabel("Julian Days")
        plt.ylabel("Lc Intensity")
        plt.show()
    # Eventually the function will return more but for now just the period
    return P


def get_accepted_result_from_file(kepid):
    df = pd.read_csv(get_answer_filename(), skiprows=31)
    df = df.set_index('kepid')
    ap = df.loc[kepid]['koi_period']
    print("ap: {}".format(ap))
    return ap


def get_accepted_result_from_db(kepid):
    rt = get_result_tbl()
    where = rt.c.kepid == kepid
    rq = sa.select([rt]).where(where)
    P = None
    with sa_engine.connect() as cur:
        row = cur.execute(rq).fetchone()
        P = row.koi_period
    return P


# 10485250 is the DB test case to use.
# 2571238 is the flat-file test case to use.
db_test = 10485250
file_test = 2571238
target_kepid = db_test
p1 = calculate_result(target_kepid, 0.5, show_valley=True, show_result=True)
real_p1 = get_accepted_result_from_db(target_kepid)
diff = abs(real_p1 - p1)
print("Error in period: {}".format(diff))
