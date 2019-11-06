#!/usr/bin/env python3

import sys
import numpy as np
import pandas as pd
import sqlalchemy as sa
import matplotlib.pyplot as plt

from math import ceil, isnan
from collections import namedtuple
from scipy.signal import find_peaks, find_peaks_cwt, argrelextrema
from scipy import signal

# Sloppy global DB connection stuff here.
sa_engine = sa.create_engine(
                'postgresql+psycopg2://kuser:kpass@localhost/kepler')
metadata = sa.MetaData()

NASAResult = namedtuple('NASAResult', 'kepoi_name kepler_name period')


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
    # Cut a median through the graph.
    # filter out the X and Y based only on Y
    # ... really should look at Pandas for this.
    # ytarget = np.median(y)
    # print("max y will be: {}".format(ytarget))
    # Ehh... that's always going to be 0 or should be since this data isnt'
    # raw.. anyway...
    ytarget = 0.00
    x, y = zip(*[(i, j) for i, j in zip(x, y) if j <= ytarget])

    if False:
        xcutline = [0, max(x)]
        ycutline = [ytarget, ytarget]
        plt.scatter(x, y, s=1)
        plt.plot(xcutline, ycutline, "m")
        plt.xlabel("Julian Days")
        plt.ylabel("Lc Intensity")
        plt.show()

    # TODO: Distance might need to be scaled down to find smaller periods
    # 10 works for 3.ish days it seems
    # valleys = find_peaks(y*-1, distance=2)[0]
    # valleys = find_peaks_cwt(y*-1, np.arange(1, 10))[0]
    valleys = argrelextrema(np.array(y), np.less, order=5)[0].tolist()

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
        # valley_x = x[good_valleys]
        # valley_y = y[good_valleys]
        valley_x = [x[i] for i in good_valleys]
        valley_y = [y[i] for i in good_valleys]
    else:
        # Should pick up other techniques here. At least log when we only
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
    # print("First stab at P: {}".format(P))
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

    # print("First transit: {}, "
    #       "Last transit (in sample): {}".format(first_trans, last_trans))
    # print("Valleys found: {}".format(valley_count))
    # Now we get a real solid estimate of the period value
    P = (last_trans - first_trans) / (valley_count - 1)
    # print("Period: {}".format(P))
    return P


# Shift every X back in time until it's relative position to transition always
# puts peak transition at time = 0.000
def phase_shift(first_transit_time, origx, origy, P):
    origx = [x - first_transit_time for x in origx]
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
    # print("looking for obs on {}".format(kepid))
    with sa_engine.connect() as cur:
        rs = cur.execute(oq).fetchall()

    # Reformat data in a very non-python way
    allx = []
    ally = []
    for row in rs:
        if isnan(row.lc_init) is False:
            allx.append(float(row.time_val))
            ally.append(float(row.lc_init))
    return allx, ally


def calculate_result(kepid, allx, ally, percentile, show_valley=False,
                     show_result=False):
    """
    kepid: Kepler Object ID (star) that we're looking at.
    percentile: Kind of a magic number at this point, generally 0.5-3%
                is where we make the threshold for a valley being legit
    TODO: This only looks for a single object, the largest one.
    """
    valley_x, valley_y = find_transit_valley(allx, ally, percentile)

    # A debbuging graph showing where we think transits are
    if len(valley_x) > 0 and show_valley:
        plt.scatter(allx, ally, s=1)
        plt.scatter(valley_x, valley_y, s=5)
        plt.xlabel("Julian Days")
        plt.ylabel("Lc Intensity with valley")
        plt.show()

    if len(valley_x) > 0:
        P = find_transit_period(valley_x, valley_y)
        allx, ally = phase_shift(valley_x[0], allx, ally, P)
    else:
        # print("Not attempting phase shift, no period detected.")
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
    return ap


def get_accepted_result_from_db(kepid):
    rt = get_result_tbl()
    where = rt.c.kepid == kepid
    rq = sa.select([rt]).where(where)
    with sa_engine.connect() as cur:
        rs = cur.execute(rq).fetchall()
    ret = []
    for row in rs:
        res = NASAResult(row.kepoi_name, row.kepler_name, row.koi_period)
        ret.append(res)
    return ret


def main_simple_test():
    # 10485250 is the DB test case to use.
    # 2571238 is the flat-file test case to use.
    db_test = 10485250
    file_test = 2571238  # noqa
    target_kepid = db_test

    allx, ally = load_kepid_from_db(target_kepid)
    p1 = calculate_result(target_kepid, allx, ally, 0.5,
                          show_valley=True, show_result=True)
    for r in get_accepted_result_from_db(target_kepid):
        real_p1 = r.period
        diff = abs(real_p1 - p1)
        print("Error in period: {}".format(diff))


def main_batch_test():
    rt = get_result_tbl()
    test_case_qry = sa.select([rt]).order_by(rt.c.koi_period)
    # Sorting by period makes as much sense as any to me.
    with sa_engine.connect() as cur:
        rs = cur.execute(test_case_qry).fetchall()

    for test_row in rs:
        kepid = test_row.kepid
        actual_period = test_row.koi_period

        # Now get observation data
        obsx, obsy = load_kepid_from_db(kepid)
        if len(obsx) == 0:
            continue  # Skip, we have no data.
        else:
            p1 = calculate_result(kepid, obsx, obsy, 0.5)
            diff = abs(actual_period - p1)
            print("kepler_id {} "
                  "period calc {} "
                  "off by {}".format(kepid, p1, diff))


def command_line_main():
    import argparse
    p = argparse.ArgumentParser(description='Kepler data analyzer')
    p.add_argument('--kepid', type=int, help='Kepler ID (int) of system')
    config = p.parse_args()

    kepid = config.kepid
    obsx, obxy = load_kepid_from_db(kepid)
    result_list = get_accepted_result_from_db(kepid)
    for r in result_list:
        print("Target period(s): {}".format(r.period))
    if len(obsx) == 0:
        print("No observation data found for {}".format(kepid))
        sys.exit(-1)

    p1 = calculate_result(kepid, obsx, obxy, 3.0,
                          show_valley=True,
                          show_result=True)
    for r in result_list:
        diff = abs(r.period - p1)
        print("kepler_id {} "
              "period calc {} "
              "off by {}".format(kepid, p1, diff))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print("Command line executing.")
        command_line_main()
    else:
        print("Batch mode executing.")
        main_batch_test()
