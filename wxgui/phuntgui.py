#!/usr/bin/env python3
import wx
import sqlalchemy as sa
import psycopg2 as pg

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


class justin(wx.Frame):

    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, 'Title', size=(300, 200))
        lpanel = wx.Panel(self)
        bload_data = wx.Button(lpanel, label='Load Data', pos=(100, 100),
                               size=(60, 60))
        self.Bind(wx.EVT_BUTTON, self.load_data, bload_data)
        self.Bind(wx.EVT_CLOSE, self.close_window)

        status_bar = self.CreateStatusBar()
        menubar_main = wx.MenuBar()
        file_menu = wx.Menu()
        edit_menu = wx.Menu()
        file_menu.Append(wx.NewIdRef(), 'Connect...', 'Connect to a new server')
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
    frame = justin(parent=None, id=-1)
    frame.Show()
    app.MainLoop()
