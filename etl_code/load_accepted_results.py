#!/usr/bin/env python3

import petl as etl
import pandas as pd
import psycopg2 as pg

NASA_SOURCE = "../kepler_accepted_results.csv"

k_conn = pg.connect(user='kuser', password='kpass',
                    host='localhost', database='kepler')

# Not using petl to pull the data in from CSV because it's CSV methods
# are a bit lacking.  Pandas does a better job here.
df = pd.read_csv(NASA_SOURCE, skiprows=31)
# df = df.set_index('kepid')

stbl = etl.fromdataframe(df, include_index=False)

# Not doing any transformation at all yet

etl.todb(stbl, k_conn, 'nasa_result', create=True, drop=False, sample=0)
k_conn.close()
