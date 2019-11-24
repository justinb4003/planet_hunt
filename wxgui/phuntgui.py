#!/usr/bin/env python3
import wx
import numpy as np
import sqlalchemy as sa

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar   # noqa
from wx.lib.splitter import MultiSplitterWindow
from matplotlib.figure import Figure
from collections import namedtuple
from math import isnan


# BEGIN DATA ROUTINES ###
sa_engine = sa.create_engine(
                'postgresql+psycopg2://kuser:kpass@192.168.1.125/kepler')
metadata = sa.MetaData()
NASAResult = namedtuple('NASAResult', 'kepoi_name kepler_name period '
                                      'first_transit koi_disposition')

OBJECT_X = []
OBJECT_Y = []


def running_mean(d, N):
    cs = np.cumsum(np.insert(d, 0, 0))
    return (cs[N:] - cs[:-N]) / float(N)


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
    # TODO: Handle db reconnect if we timed out.
    print("loading {}".format(kepid))
    ot = get_observation_tbl()
    cols = [ot.c.time_val, ot.c.lc_init]
    where = ot.c.kepler_id == kepid
    qry = sa.select(cols).select_from(ot).where(where)
    print(qry)
    with sa_engine.connect() as cur:
        rs = cur.execute(qry).fetchall()
    x = []
    y = []
    print("found {} records".format(len(rs)))
    for row in rs:
        if not isnan(row.lc_init):
            x.append(row.time_val)
            y.append(row.lc_init)
    return x, y


def get_accepted_result_from_db(kepid):
    rt = get_result_tbl()
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

    def __init__(self, parent, display_panel, modify_panel):
        wx.Panel.__init__(self, parent=parent)
        self.display_panel = display_panel
        self.modify_panel = modify_panel

        hbox = wx.BoxSizer(wx.VERTICAL)
        self.kepid = wx.TextCtrl(self)
        bload = wx.Button(self, label='Load Kepler ID')

        self.kep_choice_ddl = wx.ComboBox(self, -1, choices=[],
                                          style=wx.CB_READONLY)
        self.kep_choice_ddl.Bind(wx.EVT_COMBOBOX, self.on_kep_choice)
        # self.kep_choice_ddl.Bind(wx.EVT_TEXT, self.on_kep_choice)

        self.kepoi_name = wx.StaticText(self)
        self.kepler_name = wx.StaticText(self)
        self.result_period = wx.StaticText(self)
        self.first_transit = wx.StaticText(self)
        self.koi_disposition = wx.StaticText(self)
        self.kepoi_name.SetLabel('N/A')
        self.kepler_name.SetLabel('N/A')
        self.result_period.SetLabel('0.00')
        self.first_transit.SetLabel('0.00')
        self.koi_disposition.SetLabel('N/A')

        # self.kepid.SetValue(str('10984090'))  # A binary system
        self.kepid.SetValue(str('6922244'))  # A single system

        hbox.Add(self.kepid, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(bload, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        self.Bind(wx.EVT_BUTTON, self.load_data, bload)
        hbox.Add(self.kep_choice_ddl, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.kepoi_name, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.kepler_name, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.result_period, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.first_transit, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.koi_disposition, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        self.SetSizer(hbox)

    def on_kep_choice(self, event):
        print('fire')
        choice = self.kep_choice_ddl.GetValue()
        for r in [x for x in self.result_list if x.kepoi_name == choice]:
            self.kepoi_name.SetLabel(str(r.kepoi_name))
            self.kepler_name.SetLabel(str(r.kepler_name))
            self.result_period.SetLabel(str(r.period))
            self.first_transit.SetLabel(str(r.first_transit))
            self.koi_disposition.SetLabel(str(r.koi_disposition))
            self.modify_panel.period.SetValue(str(r.period))
            self.modify_panel.first_transit.SetValue(str(r.first_transit))
            print("Target period(s): {}".format(r.period))
            print("Target 0k(s): {}".format(r.first_transit))

    def load_data(self, event):
        kepid = None
        try:
            kepid = int(self.kepid.GetValue())
        except ValueError:
            wx.MessageBox('Unable to read Kepler ID', 'Problem!',
                          wx.OK | wx.ICON_INFORMATION)

        if kepid is not None:
            print("hit load_data().: {}".format(kepid))
            global OBJECT_X, OBJECT_Y
            OBJECT_X, OBJECT_Y = load_kepler_id_from_db(kepid)
            self.result_list = get_accepted_result_from_db(kepid)
            kep_choice = [r.kepoi_name for r in self.result_list]
            kep_choice.sort()

            self.kep_choice_ddl.Clear()
            self.kep_choice_ddl.AppendItems(kep_choice)
            # I'm intentionally not defaulting the drop-down to a default
            # selection because I don't like being shown the known data
            # without taking action.  Personal preferance.
            # .. but I still want to know why this doesn't work.
            # self.kep_choice_ddl.SetValue(kep_choice[0])
            self.display_panel.display_transit_raw(OBJECT_X, OBJECT_Y)
            print("You should see the raw transit now.")


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
        self.force_update()

    def display_shifted(self, x, y, meanx, meany):
        self.ax1.cla()
        self.ax1.scatter(x, y, s=1)
        self.ax1.plot(meanx, meany, 'm')
        self.force_update()

    def force_update(self):
        global frame
        # TODO: This isn't always forcing a redraw on some of my computers.
        self.canvas.draw()
        self.Layout()
        frame.force_update()


class DataModifyPanel(wx.Panel):

    def __init__(self, parent, display_panel):
        wx.Panel.__init__(self, parent=parent)
        self.display_panel = display_panel
        hbox = wx.BoxSizer(wx.VERTICAL)
        self.period = wx.TextCtrl(self)
        self.first_transit = wx.TextCtrl(self)
        papply_manual = wx.Button(self, label='Apply Period Shift')

        hbox.Add(self.period, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(self.first_transit, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        hbox.Add(papply_manual, 0,
                 wx.ALIGN_CENTER_HORIZONTAL | wx.ALL | wx.EXPAND, 5)
        self.Bind(wx.EVT_BUTTON, self.apply_period_manual, papply_manual)
        self.SetSizer(hbox)

    def apply_period_manual(self, event):
        global OBJECT_X, OBJECT_Y
        try:
            ftrans = float(self.first_transit.GetValue())
            period = float(self.period.GetValue())
        except ValueError:
            wx.MessageBox('Unable to read Transit/period value', 'Problem!',
                          wx.OK | wx.ICON_INFORMATION)

        print("hit apply_period_manual().: {}".format(period))
        x, y = phase_shift(ftrans, OBJECT_X, OBJECT_Y, period)
        # Take a running mean of N size for each list
        N = 551  # <-- magic number found via fiddling
        meanx = running_mean(x, N)
        meany = running_mean(y, N)

        # self.display_panel.display_transit_raw(x, y)
        # print(x)
        # print(meanx)
        # print(y)
        # print(meany)
        self.display_panel.display_shifted(x, y, meanx, meany)
        print("scatter with mean should be updated")


class MainWindow(wx.Frame):

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, 'Planet Hunt', size=(1400, 600))

        self.splitter = MultiSplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        # The passing references to panels and controsl to each other
        # seems a bit sloppy and I want to do away with it. Not sure how yet.
        data_display_panel = DataDisplayPanel(self.splitter)
        data_modify_panel = DataModifyPanel(self.splitter, data_display_panel)
        data_search_panel = DataSearchPanel(self.splitter, data_display_panel,
                                            data_modify_panel)
        self.splitter.AppendWindow(data_search_panel, sashPos=150)
        self.splitter.AppendWindow(data_display_panel, sashPos=1050)
        self.splitter.AppendWindow(data_modify_panel)

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

    def force_update(self):
        # Jiggle the splitter 'sash' around to force a redraw.
        # No, I don't like having to do this but I can't figure out the
        # proper way to make the matplotlib graphs actually show up.
        sp = self.splitter.GetSashPosition(0)
        self.splitter.SetSashPosition(0, sp+1)
        self.splitter.SetSashPosition(0, sp+0)

    def close_window(self, event):
        self.Destroy()


if __name__ == '__main__':
    app = wx.App()
    frame = MainWindow(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
