#!/usr/bin/env python3

import os
import petl as etl
import psycopg2 as pg

DATA_DIR = "/mnt/bigdata/jbuist/kepler/"

k_conn = pg.connect(user='kuser', password='kpass',
                    host='localhost', database='kepler')

# Uncomment once the table is created and you, for whatever reason
# want to truncate it when it's time to reload data.
# k_conn.cursor().execute('TRUNCATE TABLE observation')

# for f in ['kplr001025986_q1_q17_dr25_tce_01_dvt_lc.tbl']:
for f in os.listdir(DATA_DIR):
    print("Loading {}...".format(f))
    colnames = None
    time_idx = -1
    lc_idx = -1

    kepid_data = []
    time_data = []
    lc_data = []
    with open(DATA_DIR + f) as infile:
        # First grab the kepler id out of the filename
        # kplr001025986_q1_q17_dr25_tce_01_dvt_lc.tbl
        #     ^^^^^^^^^--- Kepler ID
        kepid = int(f.split('_')[0][4:])
        for line in infile:
            # Skip any lines that start with a \, as they are comments
            if line.startswith('\\'):
                continue
            if line.startswith('|') and colnames is None:
                colnames = [item.lower().strip() for item in line.split("|")
                            if len(item.lower().strip()) > 0]
                time_idx = colnames.index('time')
                lc_idx = colnames.index('lc_init')
                continue
            elif line.startswith('|'):
                continue

            dparts = line.split()
            time = float(dparts[time_idx])
            lc = float(dparts[lc_idx])
            kepid_data.append(kepid)
            time_data.append(time)
            lc_data.append(lc)

    # Now turn out python structures into something petl can work with
    stbl = etl.fromcolumns([kepid_data, time_data, lc_data],
                           header=['kepler_id', 'time_val', 'lc_init'])

    # Run with this method the first time through to have it automatically
    # create the target schema for you.
    # etl.todb(stbl, k_conn, 'observation', create=True)
    etl.appenddb(stbl, k_conn, 'observation')

k_conn.close()
