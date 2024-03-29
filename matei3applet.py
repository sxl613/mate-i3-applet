#!/usr/bin/env python3

import logging

from mate_version import import_gtk
from log import setup_logging

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import MatePanelApplet

from i3conn import I3Conn


setup_logging()
import_gtk()


DEFAULT_COLORS = {
    "background": "#000000",
    "statusline": "#ffffff",
    "separator": "#666666",
    "binding_mode_border": "#2f343a",
    "binding_mode_bg": "#900000",
    "binding_mode_text": "#ffffff",
    "active_workspace_border": "#333333",
    "active_workspace_bg": "#5f676a",
    "active_workspace_text": "#ffffff",
    "inactive_workspace_border": "#333333",
    "inactive_workspace_bg": "#222222",
    "inactive_workspace_text": "#888888",
    "urgent_workspace_border": "#2f343a",
    "urgent_workspace_bg": "#900000",
    "urgent_workspace_text": "#ffffff",
    "focused_workspace_border": "#4c7899",
    "focused_workspace_bg": "#285577",
    "focused_workspace_text": "#ffffff",
}


class i3bar(object):
    def __init__(self, applet):
        logging.debug("initializing mate-i3-applet")
        self.applet = applet
        self.applet.connect("destroy", self.destroy)
        self.i3conn = I3Conn()

        self.colors = self.init_colors()
        logging.debug("colors: {}".format(str(self.colors)))

        self.init_widgets()
        self.set_initial_buttons()

        self.open_sub()

    def __del__(self):
        self.destroy(None)

    def destroy(self, event):
        self.close_sub()

    def init_widgets(self):
        self.box = Gtk.HBox()
        self.applet.add(self.box)
        self.modeLabel = Gtk.Label("")
        self.modeLabel.set_use_markup(True)

    def set_initial_buttons(self):
        workspaces = self.i3conn.get_workspaces()
        workspaces = sorted(workspaces, key=lambda i: i["num"])
        self.set_workspace_buttons(workspaces)

    def init_colors(self):
        global DEFAULT_COLORS

        bar_ids = self.i3conn.get_bar_config_list()

        colors = None
        while not colors and bar_ids:
            bar_id = bar_ids.pop()
            bar = self.i3conn.get_bar_config(bar_id)
            colors = bar["colors"]

        return colors or DEFAULT_COLORS

    def close_sub(self):
        logging.debug("close_sub")
        self.i3conn.close()

    def open_sub(self):
        logging.debug("open_sub")
        self.i3conn.subscribe(self.on_workspace_event, self.on_mode_event)

    def on_workspace_event(self, workspaces):
        logging.debug("on_workspace_event")

        if workspaces:
            GLib.idle_add(self.set_workspace_buttons, workspaces)

    def on_mode_event(self, mode):
        logging.debug("on_mode_event")
        logging.debug(mode.change)

        GLib.idle_add(self.set_mode_label_text, mode.change)

    def set_mode_label_text(self, text):
        if text == "default":
            self.modeLabel.set_text("")
        elif all(
            key in self.colors
            for key in ("binding_mode_border", "binding_mode_bg", "binding_mode_text")
        ):
            textToSet = '<span background="%s" color="%s"><b> %s </b></span>' % (
                self.colors["binding_mode_bg"],
                self.colors["binding_mode_text"],
                text,
            )
            self.modeLabel.set_text(textToSet)
        else:
            textToSet = '<span background="%s" color="%s"><b> %s </b></span>' % (
                self.colors["urgent_workspace_bg"],
                self.colors["urgent_workspace_text"],
                text,
            )
            self.modeLabel.set_text(textToSet)

        self.modeLabel.set_use_markup(True)
        self.modeLabel.show()

    def go_to_workspace(self, workspace):
        if not workspace["focused"]:
            self.i3conn.go_to_workspace(workspace["name"])

    def set_workspace_buttons(self, workspaces):
        logging.debug("set_workspace_buttons")
        workspaces = sorted(workspaces, key=lambda i: i["num"])

        for child in self.box.get_children():
            self.box.remove(child)

        def get_workspace_bgcolor(workspace):
            if workspace["urgent"]:
                return self.colors["urgent_workspace_bg"]
            if workspace["focused"]:
                return self.colors["focused_workspace_bg"]
            return self.colors["active_workspace_bg"]

        def get_workspace_fgcolor(workspace):
            if workspace["urgent"]:
                return self.colors["urgent_workspace_text"]
            if workspace["focused"]:
                return self.colors["focused_workspace_text"]
            return self.colors["active_workspace_text"]

        def workspace_to_label(workspace):
            bgcolor = get_workspace_bgcolor(workspace)
            fgcolor = get_workspace_fgcolor(workspace)
            return '<span background="%s" color="%s"><b> %s </b></span>' % (
                bgcolor,
                fgcolor,
                workspace["name"],
            )

        def get_button(workspace):
            button = Gtk.EventBox()
            label = Gtk.Label(workspace_to_label(workspace))
            label.set_use_markup(True)
            button.add(label)
            button.connect(
                "button_press_event", lambda w, e: self.go_to_workspace(workspace)
            )
            return button

        for workspace in workspaces:
            self.box.pack_start(get_button(workspace), False, False, 0)

        self.box.pack_start(self.modeLabel, False, False, 0)
        self.box.show_all()

    def show(self):
        self.applet.show_all()


def applet_factory(applet, iid, data):
    logging.debug("iid: {}".format(iid))
    if iid != "I3Applet":
        return False

    bar = i3bar(applet)
    bar.show()

    return True


MatePanelApplet.Applet.factory_main(
    "I3AppletFactory", True, MatePanelApplet.Applet.__gtype__, applet_factory, None
)
