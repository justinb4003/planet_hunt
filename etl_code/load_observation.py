#!/usr/bin/env python3

import os
import petl as etl
import psycopg2 as pg
import sqlalchemy as sa

DATA_DIR = "/mnt/bigdata/jbuist/kepler/"

k_conn = pg.connect(user='kuser', password='kpass',
                    host='localhost', database='kepler')

sa_engine = sa.create_engine(
                'postgresql+psycopg2://kuser:kpass@localhost/kepler')
metadata = sa.MetaData()


def get_sa_table(tblname):
    tbl = sa.Table(tblname, metadata, autoload=True, autoload_with=sa_engine)
    print(tbl)
    return tbl


def get_sourcefile_metadata(fname):
    sfmt = get_sa_table('sourcefile_meta')
    cols = [sfmt.c.record_count, sfmt.c.source_uuid]
    where = sfmt.c.filename == fname
    qry = sa.select(cols).select_from(sfmt).where(where)
    with sa_engine.connect() as cur:
        row = cur.execute(qry).fetchone()

    ret_rcount = None
    ret_uuid = None

    if row is not None:
        ret_rcount = int(row.record_count)
        ret_uuid = row.source_uuid

    return ret_rcount, ret_uuid


# Uncomment once the table is created and you, for whatever reason
# want to truncate it when it's time to reload data.
# k_conn.cursor().execute('TRUNCATE TABLE observation')

# for f in ['kplr001025986_q1_q17_dr25_tce_01_dvt_lc.tbl']:

file_list = ['kplr008463346_q1_q17_dr25_tce_01_dvt_lc.tbl',
             'kplr008463346_q1_q17_dr25_tce_02_dvt_lc.tbl']

# for f in os.listdir(DATA_DIR):
for f in file_list:
    # First check to see if file was already loaded
    rcount, suuid = get_sourcefile_metadata(f)
    print(rcount, suuid)
    os.sys.exit(0)
    print("Loading {}...".format(f))
    cols = None
    time_idx = -1
    lc_idx = -1

    kepid_data = []
    time_data = []
    timecorr_data = []
    cadenceno_data = []
    phase_data = []
    lc_init_data = []
    lc_init_err_data = []
    lc_white_data = []
    lc_detrend_data = []
    model_init_data = []
    model_white_data = []
    with open(DATA_DIR + f) as infile:
        # First grab the kepler id out of the filename
        # kplr001025986_q1_q17_dr25_tce_01_dvt_lc.tbl
        #     ^^^^^^^^^--- Kepler ID
        kepid = int(f.split('_')[0][4:])
        for line in infile:
            # Skip any lines that start with a \, as they are comments
            if line.startswith('\\'):
                continue
            if line.startswith('|') and cols is None:
                cols = [item.lower().strip() for item in line.split("|")
                        if len(item.lower().strip()) > 0]
                continue
            elif line.startswith('|'):
                continue

            d = line.split()
            kepid_data.append(kepid)
            time_data.append(float(d[cols.index('time')]))
            timecorr_data.append(float(d[cols.index('timecorr')]))
            cadenceno_data.append(float(d[cols.index('cadenceno')]))
            phase_data.append(float(d[cols.index('phase')]))
            lc_init_data.append(float(d[cols.index('lc_init')]))
            lc_init_err_data.append(float(d[cols.index('lc_init_err')]))
            lc_white_data.append(float(d[cols.index('lc_white')]))
            lc_detrend_data.append(float(d[cols.index('lc_detrend')]))
            model_init_data.append(float(d[cols.index('model_init')]))
            model_white_data.append(float(d[cols.index('model_white')]))

    # Now turn out python structures into something petl can work with
    stbl = etl.fromcolumns([kepid_data, time_data, timecorr_data,
                            cadenceno_data, phase_data, lc_init_data,
                            lc_init_err_data, lc_white_data, lc_detrend_data,
                            model_init_data, model_white_data],
                           header=['kepler_id', 'time_val', 'timecorr',
                                   'cadenceno', 'phase', 'lc_init',
                                   'lc_init_err', 'lc_white', 'lc_detrend',
                                   'model_init', 'model_white'])

    # Run with this method the first time through to have it automatically
    # create the target schema for you.
    # etl.todb(stbl, k_conn, 'observation', create=True)
    with sa_engine.connect() as cur:
        etl.appenddb(stbl, cur, 'observation_full')

k_conn.close()
