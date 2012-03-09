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
import string
import traceback
from pymclevel import nbt
from pyinvedit import vmware
from pyinvedit import about_name, about_version, about_url, about_authors

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
        Runs our dialog and loads the NBT, if possible.  Returns the
        filename, or None
        """
        resp = self.run()
        if resp == gtk.RESPONSE_OK:
            filename = self.get_filename()
            if os.path.exists(filename):
                return filename
        return None

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

class ConfirmReplaceDialog(gtk.MessageDialog):
    """
    A dialog we can use to confirm whether or not to replace our
    currently-loaded file
    """

    def __init__(self, parentobj, action):
        super(ConfirmReplaceDialog, self).__init__(parentobj, 
                gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                gtk.MESSAGE_WARNING,
                gtk.BUTTONS_YES_NO)
        self.set_markup('<b>Warning:</b> There are still unsaved changes on the current level.  Really %s?' % (action))
        self.set_title('Confirm %s' % (string.capwords(action)))
        self.set_default_response(gtk.RESPONSE_YES)

class InvAboutDialog(gtk.AboutDialog):
    """
    Our About dialog
    """


    def __init__(self, parentobj):
        super(InvAboutDialog, self).__init__()

        global about_name, about_version, about_url, about_authors

        self.set_transient_for(parentobj)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_name(about_name)
        self.set_version(about_version)
        self.set_website(about_url)
        self.set_authors(about_authors)
        self.set_comments('A Minecraft Inventory Editor written in Python')
        licensepath = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'COPYING.txt')
        if os.path.isfile(licensepath):
            try:
                with open(licensepath, 'r') as df:
                    self.set_license(df.read())
            except Exception:
                pass
        iconpath = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'logo.png')
        if os.path.isfile(iconpath):
            try:
                self.set_logo(gtk.gdk.pixbuf_new_from_file(iconpath))
            except Exception, e:
                pass

class NewEnchantmentDialog(gtk.Dialog):
    """
    A dialog to add a new enchantment to an item
    """
    
    (COL_NAME, COL_OBJ, COL_SELECTABLE) = range(3)

    def __init__(self, parentobj, invdetail, slot, items, enchantments):
        super(NewEnchantmentDialog, self).__init__('Add New Enchantment',
                parentobj,
                gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OK, gtk.RESPONSE_OK))

        self.set_default_response(gtk.RESPONSE_OK)

        self.invdetail = invdetail
        self.slot = slot
        self.items = items
        self.enchantments = enchantments
        self.updating = True

        if slot is None:
            raise Exception('No valid inventory slot found')

        self.item = items.get_item(slot.num, slot.damage)
        if self.item:
            self.item_name = self.item.name
        else:
            self.item_name = 'Unknown Item %d' % (slot.num)

        # Some contents
        vbox = gtk.VBox()
        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(5, 5, 5, 5)
        align.add(vbox)
        self.vbox.pack_start(align, True, True)

        # Main title
        align = gtk.Alignment(.5, 0, 0, 0)
        align.set_padding(0, 10, 0, 0)
        label = gtk.Label()
        label.set_markup('<big><b>Add Enchantment for %s</b></big>' % (self.item_name))
        align.add(label)
        vbox.pack_start(align, False, True)

        # Table for enchantment selection
        enchtable = gtk.Table(3, 8)
        align = gtk.Alignment(0, 0, 1, 0)
        align.set_padding(5, 5, 10, 10)
        align.add(enchtable)
        vbox.pack_start(align, False, True)

        # Make two separate lists, one for valid enchantments, one for
        # invalid
        enchs = enchantments.get_all()
        valid_ench = []
        invalid_ench = []
        for ench in enchs:
            if self.item and ench in self.item.enchantments:
                valid_ench.append(ench)
            else:
                invalid_ench.append(ench)

        # ListStore for all our enchantments that we'll present
        store = gtk.ListStore(str, object, bool)
        self._add_to_store(store, 'Valid Enchantments', valid_ench)
        if len(invalid_ench) > 0 and len (valid_ench) > 0:
                iterench = store.append()
                store.set(iterench,
                        self.COL_NAME, '',
                        self.COL_OBJ, None,
                        self.COL_SELECTABLE, False)
        self._add_to_store(store, 'Invalid Enchantments', invalid_ench, True)

        # ComboBox for these presets
        self.ench_combo = gtk.ComboBox(store)
        self.ench_combo.set_entry_text_column(self.COL_NAME)
        cell = gtk.CellRendererText()
        self.ench_combo.pack_start(cell, True)
        self.ench_combo.add_attribute(cell, 'markup', self.COL_NAME)

        # Now contents
        cur_row = 0
        self._rowlabel(enchtable, cur_row, 'Preset')
        self._rowdata(enchtable, cur_row, self.ench_combo)

        # Name
        cur_row += 1
        self._rowlabel(enchtable, cur_row, 'or ID')
        adjust = gtk.Adjustment(0, -1, 32767, 1, 1)
        self.ench_id = gtk.SpinButton(adjust)
        self._rowdata(enchtable, cur_row, self.ench_id)

        # Separator
        cur_row += 1
        self._rowseparator(enchtable, cur_row)

        # ID
        cur_row += 1
        self._rowlabel(enchtable, cur_row, 'Name')
        self.ench_name = gtk.Label()
        self._rowdata(enchtable, cur_row, self.ench_name)

        # Max level identifier
        cur_row += 1
        self._rowlabel(enchtable, cur_row, 'Max Level')
        self.ench_max = gtk.Label()
        self._rowdata(enchtable, cur_row, self.ench_max)

        # Level
        cur_row += 1
        self._rowlabel(enchtable, cur_row, 'Level')
        adjust = gtk.Adjustment(0, 1, 32767, 1, 1)
        self.ench_lvl = gtk.SpinButton(adjust)
        self._rowdata(enchtable, cur_row, self.ench_lvl)

        # Separator
        cur_row += 1
        self._rowseparator(enchtable, cur_row)

        # And an HBox to show what we've selected
        cur_row += 1
        hbox = gtk.HBox()
        align = gtk.Alignment(.5, 0, 0, 0)
        align.set_padding(5, 5, 5, 5)
        align.add(hbox)
        enchtable.attach(align, 0, 3, cur_row, cur_row+1, gtk.FILL, gtk.FILL)
        label = gtk.Label()
        label.set_markup('<b>Selected:</b>')
        hbox.pack_start(label, False, True, 5)
        self.selected_text = gtk.Label()
        self.selected_text.set_markup('<i>None</i>')
        hbox.add(self.selected_text)

        # Connect some signals
        self.ench_combo.connect('changed', self.choose_preset)
        self.ench_id.connect('changed', self.spin_changed)
        self.ench_lvl.connect('changed', self.spin_changed)

        # Make sure everything gets shown
        self.show_all()

        self.updating = False

    def _add_to_store(self, store, title, enchantments, ital=False):
        """
        Adds a list of enchantments to the given store, with the given
        title above
        """
        if len(enchantments) > 0:
            iterench = store.append()
            store.set(iterench,
                    self.COL_NAME, '<b>%s:</b>' % (title),
                    self.COL_OBJ, None,
                    self.COL_SELECTABLE, False)
            for ench in enchantments:
                if ital:
                    name = '<i>%s</i>' % (ench.name)
                else:
                    name = ench.name
                iterench = store.append()
                store.set(iterench,
                        self.COL_NAME, '   %s' % (name),
                        self.COL_OBJ, ench,
                        self.COL_SELECTABLE, True)

    def _rowlabel(self, table, row, text):
        """
        A row label
        """
        align = gtk.Alignment(1, .5, 0, 0)
        align.set_padding(0, 0, 0, 5)
        label = gtk.Label()
        label.set_markup('<b>%s:</b>' % (text))
        align.add(label)
        table.attach(align, 0, 1, row, row+1, gtk.FILL, gtk.FILL)

    def _rowdata(self, table, row, widget):
        """
        A data widget, just wrapped up in an Alignment
        """
        align = gtk.Alignment(0, 0, 0, 0)
        align.add(widget)
        table.attach(align, 1, 2, row, row+1, gtk.FILL, gtk.FILL)

    def _rowseparator(self, table, row):
        """
        A separator
        """
        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(15, 15, 10, 10)
        sep = gtk.HSeparator()
        align.add(sep)
        table.attach(align, 0, 2, row, row+1, gtk.FILL|gtk.EXPAND, gtk.FILL)

    def choose_preset(self, widget, param=None):
        """
        User chose an enchantment from our dropdown
        """
        if self.updating:
            return
        self.updating = True
        model = self.ench_combo.get_model()
        iterench = self.ench_combo.get_active_iter()
        if iterench is not None:
            selectable = model.get_value(iterench, self.COL_SELECTABLE)
            if selectable:
                ench = model.get_value(iterench, self.COL_OBJ)
                self.ench_id.set_value(ench.num)
                self.ench_name.set_text(ench.name)
                self.ench_lvl.set_value(ench.max_power)
                self.ench_max.set_text(str(ench.max_power))
                self.update_chosen()
            else:
                self.ench_combo.set_active(-1)
        self.updating = False

    def spin_changed(self, widget, param=None):
        """
        One of our spinbuttons changed
        """
        if self.updating:
            return
        self.updating = True
        if widget == self.ench_id:
            ench = self.enchantments.get_by_id(self.ench_id.get_value())
            if ench:
                self.ench_name.set_text(ench.name)
                self.ench_lvl.set_value(ench.max_power)
                self.ench_max.set_text(str(ench.max_power))
            else:
                self.ench_name.set_text('Unknown Enchantment %d' % (self.ench_id.get_value()))
            found = False
            for idx, row in enumerate(self.ench_combo.get_model()):
                obj = row[self.COL_OBJ]
                if obj:
                    if obj.num == self.ench_id.get_value():
                        self.ench_combo.set_active(idx)
                        found = True
                        break
            if not found:
                self.ench_combo.set_active(-1)
        self.update_chosen()
        self.updating = False

    def update_chosen(self):
        """
        Updates our info about which enchantment we've chosen
        """
        if self.ench_id.get_value() >= 0:
            text = self.enchantments.get_text(self.ench_id.get_value(), self.ench_lvl.get_value())
        else:
            text = 'None'
        self.selected_text.set_markup('<i>%s</i>' % (text))
