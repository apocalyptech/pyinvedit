#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:
#
# Copyright (c) 2012, Christopher J. Kucera
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the PyInvEdit team nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL VINCENT VOLLERS OR CJ KUCERA BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import gtk
import pango
import traceback
from pymclevel import nbt
from pyinvedit import vmware

class SaveAsDialog(gtk.FileChooserDialog):
    """
    A class to support "Save As"
    """
    def __init__(self, parent):
        super(SaveAsDialog, self).__init__('Save As...', parent,
                gtk.FILE_CHOOSER_ACTION_SAVE,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_SAVE, gtk.RESPONSE_OK))
        self.set_default_response(gtk.RESPONSE_CANCEL)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_filename(parent.filename)
        self.set_do_overwrite_confirmation(True)
        self.overwrite_all = False
        self.connect('confirm-overwrite', self.on_confirm_overwrite)
        filter = gtk.FileFilter()
        filter.set_name(".dat files")
        filter.add_pattern("*.dat")
        self.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.add_filter(filter)

    def on_confirm_overwrite(self, chooser, param=None):
        """
        Our own custom overwrite-confirm dialog
        """
        try:
            # Try to load it as NBT, and then try to access an Inventory
            # structure.  If we succeed, then we're trying to save-as
            # an existing Minecraft level.dat, so we should use our custom
            # dialog to see if the user wants to overwrite fully, or just
            # do the inventory stuff.  Otherwise, just use the default
            # dialog.
            nbtdata = nbt.load(self.get_filename())
            test = nbtdata['Data'].value['Player'].value['Inventory'].value
        except Exception:
            self.overwrite_all = True
            return gtk.FILE_CHOOSER_CONFIRMATION_CONFIRM
        dialog = OverwriteConfirmDialog(self, filename=self.get_filename())
        result = dialog.run()
        self.overwrite_all = dialog.is_overwrite_all()
        dialog.destroy()
        if result == gtk.RESPONSE_YES:
            return gtk.FILE_CHOOSER_CONFIRMATION_ACCEPT_FILENAME
        else:
            return gtk.FILE_CHOOSER_CONFIRMATION_SELECT_AGAIN

    def is_overwrite_all(self):
        """
        Return whether or not we've overwriting everything
        """
        return self.overwrite_all

class ExceptionDialog(gtk.Dialog):
    """
    Dialog to show an exception
    """

    def __init__(self, parentobj, title, text, exception):
        super(ExceptionDialog, self).__init__(title,
                parentobj,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_OK, gtk.RESPONSE_OK))

        self.set_size_request(650, 300)
        self.set_default_response(gtk.RESPONSE_OK)

        # Contents
        hbox = gtk.HBox()
        self.vbox.add(hbox)

        icon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_DIALOG)
        align = gtk.Alignment(.5, .5, 0, 0)
        align.set_padding(20, 20, 20, 20)
        align.add(icon)
        hbox.pack_start(align, False, True)

        vbox = gtk.VBox()
        hbox.pack_start(vbox, True, True)

        align = gtk.Alignment(0, 0, 1, 0)
        align.set_padding(10, 5, 5, 5)
        label = vmware.WrapLabel()
        label.set_markup(text)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(pango.WRAP_WORD_CHAR)
        align.add(label)
        vbox.pack_start(align, False, True)

        align = gtk.Alignment(.5, .5, 0, 0)
        align.set_padding(5, 10, 5, 5)
        label = gtk.Label()
        label.set_markup('<b>%s</b>' % (str(exception)))
        align.add(label)
        vbox.pack_start(align, False, True)

        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(0, 10, 20, 10)
        exc_type, exc_value, exc_tb = sys.exc_info()
        exc_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        exbuffer = gtk.TextBuffer()
        exbuffer.set_text(exc_str)
        tv = gtk.TextView(exbuffer)
        tv.set_editable(False)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(tv)
        align.add(sw)
        vbox.pack_start(align, True, True)

        self.show_all()

class LoaderDialog(gtk.FileChooserDialog):
    """
    A class to load a new minecraft save.
    """
    def __init__(self, parent):
        self.parentobj = parent
        super(LoaderDialog, self).__init__('Open New Savegame', parent,
                gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_current_folder(os.path.join(os.path.expanduser('~'), '.minecraft', 'saves'))
        filter = gtk.FileFilter()
        filter.set_name(".dat files")
        filter.add_pattern("*.dat")
        self.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.add_filter(filter)

    def load(self):
        """
        Runs our dialog and loads the NBT, if possible.  Returns a tuple
        with the filename and the NBT structure.
        """
        resp = self.run()
        if resp == gtk.RESPONSE_OK:
            filename = self.get_filename()
            if os.path.exists(filename):
                try:
                    return (filename, nbt.load(filename))
                except Exception, e:
                    dialog = ExceptionDialog(self.parentobj,
                            'Error Loading File',
                            "There was an error loading the file:\n<tt>%s</tt>" % (filename),
                            e)
                    dialog.run()
                    dialog.destroy()
        return (None, None)

class OverwriteConfirmDialog(gtk.Dialog):
    """
    Class to confirm overwrite of a level file
    """

    def __init__(self, parentobj, name=None, filename=None):
        super(OverwriteConfirmDialog, self).__init__('Confirm Overwrite',
                parentobj, 
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_YES, gtk.RESPONSE_YES,
                    gtk.STOCK_NO, gtk.RESPONSE_NO))

        # Contents
        hbox = gtk.HBox()
        self.vbox.add(hbox)

        icon = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)
        align = gtk.Alignment(.5, .5, 0, 0)
        align.set_padding(20, 20, 20, 20)
        align.add(icon)
        hbox.pack_start(align, False, True)

        vbox = gtk.VBox()
        hbox.pack_start(vbox, True, True)
        
        align = gtk.Alignment(0, 0, 0, 0)
        align.set_padding(10, 10, 5, 5)
        label = gtk.Label()
        if name is not None:
            label.set_markup('Really overwrite the savefile named "%s"?' % (name))
        elif filename is not None:
            label.set_markup('Really overwrite the savefile at "<tt>%s</tt>"?' % (filename))
        else:
            label.set_markup('Really overwrite the savefile?')
        align.add(label)
        vbox.pack_start(align, False, True)

        align = gtk.Alignment(0, 0, 0, 0)
        align.set_padding(0, 0, 20, 0)
        self.overwrite_inv = gtk.RadioButton(label='Only overwrite the inventory')
        align.add(self.overwrite_inv)
        vbox.pack_start(align, False, True)

        align = gtk.Alignment(0, 0, 0, 0)
        align.set_padding(0, 0, 20, 0)
        self.overwrite_all = gtk.RadioButton(group=self.overwrite_inv, label='Overwrite entire file <i>(including seed, position, etc)</i>')
        self.overwrite_all.child.set_use_markup(True)
        align.add(self.overwrite_all)
        vbox.pack_start(align, True, True)

        self.show_all()

    def is_overwrite_all(self):
        """
        Return whether or not we've overwriting everything
        """
        return self.overwrite_all.get_active()
