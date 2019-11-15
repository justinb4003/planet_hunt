#!/usr/bin/env python3
import wx
import sqlalchemy as sa

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar   # noqa
from wx.lib.splitter import MultiSplitterWindow
from matplotlib.figure import Figure
from collections import namedtuple


# BEGIN DATA ROUTINES ###
sa_engine = sa.create_engine(
                'postgresql+psycopg2://kuser:kpass@192.168.1.125/kepler')
metadata = sa.MetaData()
NASAResult = namedtuple('NASAResult', 'kepoi_name kepler_name period')

OBJECT_X = []
OBJECT_Y = []


def get_sa_table(tblname):
    tbl = sa.Table(tblname, metadata, autoload=True, autoload_with=sa_engine)
    print(tbl)
    return tbl


def get_observation_tbl():
    tbl = get_sa_table('observation_full')
    return tbl


def get_result_tbl():
    return get_sa_table('nasa_result')


def load_kepler_id_from_db(kepid):
    print("loading {}".format(kepid))
    ot = get_observation_tbl()
    cols = [ot.c.time_val, ot.c.lc_init]
    where = ot.c.kepler_id == kepid
    qry = sa.select(cols).select_from(ot).where(where)
    with sa_engine.connect() as cur:
        rs = cur.execute(qry).fetchall()
    x = []
    y = []
    print("found {} records".format(len(rs)))
    for row in rs:
        x.append(row.time_val)
        y.append(row.lc_init)
    print("now returning them.")
    return x, y


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

# END DATA ROUTINES ###


# data manipulation #
# TODO: Not sure where to put these yet

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

# end data manipulation


class DataSearchPanel(wx.Panel):

    def __init__(self, parent, display_panel):
        wx.Panel.__init__(self, parent=parent)
        self.display_panel = display_panel

        hbox = wx.BoxSizer(wx.VERTICAL)
        self.kepid = wx.TextCtrl(self)
        bload = wx.Button(self, label='Load Kepler ID')

        hbox.Add(self.kepid, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(bload, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        self.Bind(wx.EVT_BUTTON, self.load_data, bload)
        self.SetSizer(hbox)

    def load_data(self, event):
        try:
            kepid = int(self.kepid.GetValue())
        except ValueError:
            # BAD: Just shove a debug value in for now.
            kepid = 5358624

        print("hit load_data().: {}".format(kepid))
        global OBJECT_X, OBJECT_Y
        OBJECT_X, OBJECT_Y = load_kepler_id_from_db(kepid)
        result_list = get_accepted_result_from_db(kepid)
        for r in result_list:
            print("Target period(s): {}".format(r.period))

        self.display_panel.display_transit_raw(OBJECT_X, OBJECT_Y)
        print("You should see the magic now.")


class DataDisplayPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)

        self.fig = Figure((3, 3), 75)
        self.canvas = FigureCanvas(self, -1, self.fig)
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()

        self.ax1 = self.fig.add_subplot(1, 1, 1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx. GROW)
        sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()

    def display_transit_raw(self, x, y):
        self.ax1.cla()
        self.ax1.scatter(x, y, s=1)
        self.canvas.draw()


class DataModifyPanel(wx.Panel):

    def __init__(self, parent, display_panel):
        wx.Panel.__init__(self, parent=parent)
        self.display_panel = display_panel
        self.SetSize((100, -1))
        hbox = wx.BoxSizer(wx.VERTICAL)
        self.period = wx.TextCtrl(self)
        papply_manual = wx.Button(self, label='Apply Period Shift')

        hbox.Add(self.period, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(papply_manual, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        self.Bind(wx.EVT_BUTTON, self.apply_period_manual, papply_manual)
        self.SetSizer(hbox)

    def apply_period_manual(self, event):
        global OBJECT_X, OBJECT_Y
        # period = float(self.period.GetValue())
        period = 3.52563
        print("hit apply_period_manual().: {}".format(period))
        x, y = phase_shift(0, OBJECT_X, OBJECT_Y, period)
        self.display_panel.display_transit_raw(x, y)
        print("scatter should be updated")


class MainWindow(wx.Frame):

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, 'Planet Hunt', size=(800, 600))

        splitter = MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        data_display_panel = DataDisplayPanel(splitter)
        data_search_panel = DataSearchPanel(splitter, data_display_panel)
        data_modify_panel = DataModifyPanel(splitter, data_display_panel)
        splitter.AppendWindow(data_search_panel, sashPos=150)
        splitter.AppendWindow(data_display_panel, sashPos=400)
        splitter.AppendWindow(data_modify_panel)

        status_bar = self.CreateStatusBar()
        menubar_main = wx.MenuBar()
        file_menu = wx.Menu()
        edit_menu = wx.Menu()
        file_menu.Append(wx.NewIdRef(), 'Connect...',
                         'Connect to a new server')
        file_menu.Append(wx.NewIdRef(), 'Close', 'Quit the application')
        menubar_main.Append(file_menu, 'File')
        menubar_main.Append(edit_menu, 'Edit')
        self.SetMenuBar(menubar_main)
        self.SetStatusBar(status_bar)

    def close_window(self, event):
        self.Destroy()

    def load_data(self, event):
        msg = wx.TextEntryDialog(None, 'Enter Kepler ID to view', 'Enter ID',
                                 '')
        if msg.ShowModal() == wx.ID_OK:
            kepid = msg.GetValue()
            load_kepler_id_from_db(kepid)

        msg.Destroy()


if __name__ == '__main__':
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
