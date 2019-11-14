#!/usr/bin/env python3
import wx
import sqlalchemy as sa

# BEGIN DATA ROUTINES ###
sa_engine = sa.create_engine(
                'postgresql+psycopg2://kuser:kpass@192.168.1.125/kepler')
metadata = sa.MetaData()


def get_sa_table(tblname):
    tbl = sa.Table(tblname, metadata, autoload=True, autoload_with=sa_engine)
    print(tbl)
    return tbl


def get_observation_tbl():
    tbl = get_sa_table('observation_full')
    return tbl


def load_kepler_id_from_db(kepid):
    kepid = 5358624
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

# END DATA ROUTINES ###


class DataSearchPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
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
        print("hit load_data().: {}".format(self.kepid.GetValue()))


class DataDisplayPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent)
        # Need to put something here, right?
        pass


class MainWindow(wx.Frame):

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, 'Planet Hunt', size=(800, 600))

        sp1 = wx.SplitterWindow(self)
        data_search_panel = DataSearchPanel(sp1)
        data_display_panel = DataDisplayPanel(sp1)
        sp1.SplitVertically(data_search_panel, data_display_panel)
        sp1.SetMinimumPaneSize(200)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(sp1, 1, wx.EXPAND)
        self.SetSizer(sizer)

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
