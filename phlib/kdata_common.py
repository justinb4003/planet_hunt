# Common functions for collecting data from the Kepler DB
import sqlalchemy as sa

from math import isnan
from functools import lru_cache
from collections import namedtuple
from datetime import datetime, timedelta


sa_engine = None
metadata = None
NASAResult = namedtuple('NASAResult', 'kepoi_name kepler_name period '
                                      'first_transit koi_disposition')

# This is really sloppy.  It'll be a bit before I untangle the UI
# and data properly.
# Right now I'm just breaking this all out so I can properly work from a
# python console and tinker with pandas


def connect():
    global sa_engine, metadata  # TODO: Still not sure I need this.
    sa_engine = sa.create_engine(
                    'postgresql+psycopg2://kuser:kpass@192.168.1.125/kepler')
    metadata = sa.MetaData()


# Nobody's calling this anymore, but leaving it around anyway
"""
def get_sa_engine():
    return sa_engine
"""


def _get_sa_table(tblname):
    tbl = sa.Table(tblname, metadata, autoload=True, autoload_with=sa_engine)
    print(tbl)
    return tbl


def _get_observation_tbl():
    tbl = _get_sa_table('observation_full')
    return tbl


def _get_result_tbl():
    return _get_sa_table('nasa_result')


def get_lc_by_kepid(kepid):
    """
    Returns a list of time and list of raw light cuve intensitity (lc_init)
    readings from the Kepler observations.

    Doesn't offer any filtering on which quarter to pull from.  Perhaps it
    should. At the least that data should filter back to the UI somehow.
    That will be something for me to expand on shortly.
    """
    # TODO: Handle db reconnect if we timed out.
    print("loading {}".format(kepid))
    ot = _get_observation_tbl()
    cols = [ot.c.time_val, ot.c.lc_init]
    where = ot.c.kepler_id == kepid
    qry = sa.select(cols).select_from(ot).where(where)
    print(qry)
    with sa_engine.connect() as cur:
        rs = cur.execute(qry).fetchall()
    x = []
    y = []
    ts_time = []  # Not currently used. :(
    print("found {} records".format(len(rs)))
    for row in rs:
        if not isnan(row.lc_init):
            # Noon 2009-01-01, the start date for kepler data
            ts = datetime(2009, 1, 1, 12, 0, 0)
            ts += timedelta(days=row.time_val)
            ts_time.append(ts)
            x.append(row.time_val)
            y.append(row.lc_init)
    return x, y


def get_result_list(kepid):
    """
    Returns a list of the accepted NASA findings for a given Kepler ID
    """
    rt = _get_result_tbl()
    where = rt.c.kepid == kepid
    rq = sa.select([rt]).where(where)
    with sa_engine.connect() as cur:
        rs = cur.execute(rq).fetchall()
    ret = []
    for row in rs:
        res = NASAResult(row.kepoi_name, row.kepler_name, row.koi_period,
                         row.koi_time0bk, row.koi_disposition)
        ret.append(res)
    return ret


@lru_cache(maxsize=1)
def get_accepted_result_kepid_list():
    """
    Return an ordered list of every Kepler ID that we've got in our
    NASA result set.  Useful if you want to page through that data which is
    exactly what I'm going to do with it.
    """
    rt = _get_result_tbl()
    cols = [rt.c.kepid]
    rq = sa.select(cols).select_from(rt).order_by(rt.c.kepid)
    with sa_engine.connect() as cur:
        rs = cur.execute(rq).fetchall()
    ret = []
    for row in rs:
        ret.append(row.kepid)
    return ret


# Some shorcutnames to comon functions.
# Basically here because I expect this to be used in an interpreter a lot
getlc = get_lc_by_kepid
getreslist = get_accepted_result_kepid_list
