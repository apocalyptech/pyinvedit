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
import gtk
import math
import yaml
import cairo
import pango
import cStringIO
import pangocairo
import collections
from pymclevel import nbt, mclevelbase
from pyinvedit import dialogs
from pyinvedit import about_name, about_version

def get_pixbuf_from_surface(surface):
    """
    Returns our currently-displayed image as a gtk.gdk.Pixbuf
    We ended up needing to call this from various places, and
    cairo.ImageSurface isn't subclassable, as it turns out.  So,
    out here as global function it went.
    """
    df = cStringIO.StringIO()
    surface.write_to_png(df)
    loader = gtk.gdk.PixbufLoader()
    loader.write(df.getvalue())
    loader.close()
    df.close()
    return loader.get_pixbuf()

class Undo(object):
    """
    Right now this is a dummy object which only keeps track of
    whether or not something's been changed since the savefile's been
    loaded.  We're doing it this way instead of just using a var
    because that way if we ever DO implement a full undo/redo, we'll
    have less conversion work.
    """

    def __init__(self):
        self.changed = False

    def change(self):
        """
        We've changed something in our file
        """
        self.changed = True

    def load(self):
        """
        We loaded a new file.
        """
        self.changed = False

    def save(self):
        """
        We saved our file
        """
        self.changed = False

    def is_changed(self):
        """
        Return whether or not we've been changed
        """
        return self.changed

# We'll make this a global var so that any of our classes can access
# it.  Probably not a very clean way of doing things, but it will
# probably prevent having to pass a bunch more references around, etc.
undo = Undo()

class TexFile(object):
    """
    Class to provide information about a specific texture file we have
    access to.
    """

    size_small = 16
    size_large = 32
    large_full = 50

    def __init__(self, yamlobj):
        """
        Initializes given a yaml dict.
        """
        self.texfile = yamlobj['texfile']
        self.x = yamlobj['dimensions'][0]
        self.y = yamlobj['dimensions'][1]
        self.grid_large = []
        self.grid_small = []
        self.grid_pixbuf = []
        for x in range(0, self.x):
            self.grid_large.append([])
            self.grid_small.append([])
            self.grid_pixbuf.append([])
            for y in range(0, self.y):
                self.grid_large[x].append(None)
                self.grid_small[x].append(None)
                self.grid_pixbuf[x].append(None)

        # Make sure the file is present
        if not os.path.exists(self.texfile):
            raise Exception('texfile %s not found' % (self.texfile))

        # And while we're at it, load and process it
        mainsurface = None
        try:
            mainsurface = cairo.ImageSurface.create_from_png(self.texfile)
        except Exception, e:
            raise Exception('Unable to load texture file %s: %s' %
                    (self.texfile, str(e)))

        # A couple of sanity checks
        main_width = int(mainsurface.get_width() / self.x)
        main_height = int(mainsurface.get_height() / self.y)
        if main_width != main_height:
            raise Exception('texfile %s is not composed of square icons' %
                    (self.texfile))
        if (main_width % 16) != 0:
            raise Exception('texfile %s width is not a factor of 16' %
                    (self.texfile))
        self.icon_width = main_width

        # Now do the actual picking-apart
        scale_small = 1
        scale_large = 1
        if self.icon_width != self.size_small:
            scale_small = self.icon_width/float(self.size_small)
        if self.icon_width != self.size_large:
            scale_large = self.icon_width/float(self.size_large)
        pat = cairo.SurfacePattern(mainsurface)
        for x in range(0, self.x):
            for y in range(0, self.y):

                # Resize for small icons (in the search pane)
                ind_surf = cairo.ImageSurface(mainsurface.get_format(), self.size_small, self.size_small)
                scaler = cairo.Matrix()
                scaler.translate(x*self.icon_width, y*self.icon_width)
                scaler.scale(scale_small, scale_small)
                pat.set_filter(cairo.FILTER_NEAREST)
                pat.set_matrix(scaler)
                ctx = cairo.Context(ind_surf)
                ctx.set_source(pat)
                ctx.paint()
                self.grid_small[x][y] = ind_surf

                # Convert "small" to a pixbuf, for ease of putting it in
                # our item selection area
                self.grid_pixbuf[x][y] = get_pixbuf_from_surface(ind_surf)

                # Resize for large icons (in the main inventory area)
                ind_surf = cairo.ImageSurface(mainsurface.get_format(), self.size_large, self.size_large)
                scaler = cairo.Matrix()
                scaler.translate(x*self.icon_width, y*self.icon_width)
                scaler.scale(scale_large, scale_large)
                pat = cairo.SurfacePattern(mainsurface)
                pat.set_filter(cairo.FILTER_NEAREST)
                pat.set_matrix(scaler)
                ctx = cairo.Context(ind_surf)
                ctx.set_source(pat)
                ctx.paint()
                self.grid_large[x][y] = ind_surf

    def check_bounds(self, x, y):
        """
        Checks to make sure that the given coordinates are within our
        range of possible icons.  Will raise an Exception if not.
        """
        if x >= self.x or x < 0 or y >= self.y or y < 0:
            raise Exception("Texture coordinate (%d, %d) is not valid for %s" %
                    (x, y, self.texfile))

    def get_tex(self, x, y, large=False):
        """
        Returns a cairo ImageSurface of the requested texture.
        """
        self.check_bounds(x, y)
        if large:
            return self.grid_large[x][y]
        else:
            return self.grid_small[x][y]

    def get_pixbuf(self, x, y):
        """
        Returns a gtk.gtk.Pixbuf of the requested texture.  Note that
        this will always be the "small" version
        """
        self.check_bounds(x, y)
        return self.grid_pixbuf[x][y]

class Group(object):
    """
    Class to hold information about our item groupings.
    """
    def __init__(self, yamlobj, texfiles):
        """
        Initializes given a YAML dict and a dict of valid texfiles
        """
        self.name = yamlobj['name']
        if yamlobj['texfile'] not in texfiles.keys():
            raise Exception('texfile %s not found for group %s' %
                    (yamlobj['texfile'], self.name))
        self.texfile = texfiles[yamlobj['texfile']]
        self.x = yamlobj['coords'][0]
        self.y = yamlobj['coords'][1]
        self.texfile.check_bounds(self.x, self.y)
        self.items = []

    def add_item(self, item):
        """
        Adds a new item to this group.
        """
        self.items.append(item)

    def get_pixbuf(self):
        """
        Returns the small gtk.gdk.Pixbuf corresponding to this item
        """
        return self.texfile.get_pixbuf(self.x, self.y)

class Enchantment(object):
    """
    Class to hold information about an enchantment
    """
    def __init__(self, yamlobj):
        self.num = yamlobj['num']
        self.name = yamlobj['name']
        self.max_power = yamlobj['max_power']

    def __cmp__(self, other):
        """
        Comparator for sorting
        """
        return cmp(self.name, other.name)

class Enchantments(object):
    """
    A class to hold a collection of enchantments
    """

    numeral_map = zip(
        (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
        ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    )

    def __init__(self):
        self.enchantments_id = {}
        self.enchantments_name = {}

    def add_enchantment(self, yamlobj):
        """
        Adds a new enchantment, given a YAML object
        """
        ench = Enchantment(yamlobj)

        # Store by ID
        if ench.num in self.enchantments_id:
            raise Exception('Enchantment ID %d is defined twice' % (ench.num))
        else:
            self.enchantments_id[ench.num] = ench

        # Store by Name
        lower = ench.name.lower()
        if lower in self.enchantments_name:
            raise Exception('Enchantment with a name "%s" is defined twice' % (ench.name))
        else:
            self.enchantments_name[lower] = ench

    def get_all(self):
        """
        Returns a list of all known enchantments
        """
        ench = self.enchantments_id.values()
        ench.sort()
        return ench

    def get_by_id(self, num):
        """
        Gets an enchantment by ID, if possible
        """
        if num in self.enchantments_id:
            return self.enchantments_id[num]
        else:
            return None

    def get_by_name(self, name):
        """
        Get an enchantment by name, if possible
        """
        lower = name.lower()
        if lower in self.enchantments_name:
            return self.enchantments_name[lower]
        else:
            return None

    def get_text(self, num, level):
        """
        Gets a text representation of a given enchantment
        """
        ench = self.get_by_id(num)
        if ench is None:
            title = 'Unknown Enchantment'
        else:
            title = ench.name
        return '%s %s' % (title, self.int_to_roman(level))

    def int_to_roman(self, i):
        """
        This version taken from one of the suggestions at
        http://code.activestate.com/recipes/81611-roman-numerals/

        I've only actually tested it out to 20, so YMMV.
        """
        result = []
        for integer, numeral in self.numeral_map:
            count = int(i / integer)
            result.append(numeral * count)
            i -= integer * count
        return ''.join(result)

class Item(object):
    """
    Class to hold information about an inventory item.
    """
    def __init__(self, yamlobj, texfiles, groups, enchantment_catalog, unknown=False):
        """
        Initializes given a YAML dict, a dict of valid texfiles, and a dict
        of valid groups
        """
        self.num = yamlobj['num']
        self.name = yamlobj['name']
        if yamlobj['texfile'] not in texfiles.keys():
            raise Exception('texfile %s not found for item %d (%s)' %
                    (yamlobj['texfile'], self.num, self.name))
        self.texfile = texfiles[yamlobj['texfile']]
        self.x = yamlobj['coords'][0]
        self.y = yamlobj['coords'][1]
        self.unknown = unknown
        self.texfile.check_bounds(self.x, self.y)
        self.enchantment_catalog = enchantment_catalog

        # See if we belong to any groups.  Note that we're adding ourselves
        # into the group object as well
        self.groups = []
        if 'groups' in yamlobj:
            for group in yamlobj['groups']:
                if group in groups:
                    self.groups.append(groups[group])
                    groups[group].add_item(self)
                else:
                    raise Exception('Group %s not found for item %d (%s)' %
                            (group, self.num, self.name))

        # Data value, if we have it.
        if 'data' in yamlobj:
            self.data = yamlobj['data']
            self.unique_id = '%d~%d' % (self.num, self.data)
        else:
            self.data = 0
            self.unique_id = self.num

        # Maximum damage, if we have it
        if 'max_damage' in yamlobj:
            self.max_damage = yamlobj['max_damage']
        else:
            self.max_damage = None

        # Maximum quantity, if we have it
        if 'max_quantity' in yamlobj:
            self.max_quantity = yamlobj['max_quantity']
        else:
            self.max_quantity = 64

        # all_data, if we have it
        if 'all_data' in yamlobj:
            self.all_data = yamlobj['all_data']
        else:
            self.all_data = False

        # See if we have any enchantments
        self.enchantments = []
        if 'enchantments' in yamlobj:
            for ench in yamlobj['enchantments']:
                enchobj = enchantment_catalog.get_by_name(ench)
                if enchobj is None:
                    raise Exception('Enchantment %s for item %s is unknown' % (ench, self.name))
                else:
                    self.enchantments.append(enchobj)

    def get_image(self, large=False):
        """
        Returns the base cairo ImageSurface for this item
        """
        return self.texfile.get_tex(self.x, self.y, large)

    def get_pixbuf(self):
        """
        Returns the small gtk.gdk.Pixbuf corresponding to this item
        """
        return self.texfile.get_pixbuf(self.x, self.y)

    def get_new_inventoryslot(self, slot):
        """
        Returns a fresh InventorySlot object based on this abstract item.
        Will fill to max quantity, etc.
        """
        return InventorySlot(num=self.num, damage=self.data, count=self.max_quantity, slot=slot)

    def __cmp__(self, other):
        """
        Comparator for sorting
        """
        return cmp(self.name, other.name)

class ItemCollection(object):
    """
    Class to hold our collection of items.  We do this rather than
    just an OrderedDict so that we can abstract the ridiculous
    uniqueid stuff, so that we can match on the data values we
    get from the Minecraft file, or from the user.
    """

    def __init__(self):
        self.items = collections.OrderedDict()

    def add_item(self, item):
        self.items[item.unique_id] = item

    def get_item(self, num, damage):
        """
        Gets an item with the given ID and damage
        """
        for unique in ['%d~%d' % (num, damage), num]:
            if unique in self.items:
                return self.items[unique]
        return None

    def get_items(self):
        """
        Returns a list of all our items, ordered.
        """
        itemlist = self.items.values()
        itemlist.sort()
        return itemlist

class EnchantmentSlot(object):
    """
    Holds information about a particular enchantment inside a particular inventory slot
    """

    def __init__(self, nbtobj=None, num=None, lvl=None):
        """
        Initializes a new object.  Either pass in 'nbtobj' or
        both 'num' and 'lvl'
        """
        if nbtobj is None:
            self.num = num
            self.lvl = lvl
            self.extratags = {}
        else:
            self.num = nbtobj.value['id'].value
            self.lvl = nbtobj.value['lvl'].value
            self.extratags = {}
            for tagname, value in nbtobj.value.iteritems():
                if tagname not in ['id', 'lvl']:
                    self.extratags[tagname] = value

    def copy(self):
        """
        Returns a fresh object with our data
        """
        newench = EnchantmentSlot(num=self.num, lvl=self.lvl)
        newench.extratags = self.extratags
        return newench

    def export_nbt(self):
        """
        Exports ourself as an NBT object
        """
        nbtobj = nbt.TAG_Compound()
        nbtobj['id'] = nbt.TAG_Short(self.num)
        nbtobj['lvl'] = nbt.TAG_Short(self.lvl)
        for tagname, tagval in self.extratags.iteritems():
            nbtobj[tagname] = tagval
        return nbtobj

    def has_extra_info(self):
        """
        Returns whether or not we have any extra information
        """
        return (len(self.extratags) > 0)

class InventorySlot(object):
    """
    Holds information about a particular inventory slot.  We make an effort to
    never lose any data that we don't explicitly understand, and so you'll see
    two extra dicts in here with the names extratags and extratagtags.  The
    first holds extra tag information stored right at the "Slot" level of
    the NBT structure.  Before we enabled explicit support for enchantments,
    this is the variable which held and saved enchantment information.

    Since adding in Enchantments explicitly, extratagtags is used to store
    extra tag information found alongside enchantments.  The enchantments
    themselves are found in an "ench" tag which itself lives inside a tag
    helpfully labeled "tag," hence the odd naming of "extratagtags."  Alas!
    """

    def __init__(self, nbtobj=None, other=None, num=None, damage=None, count=None, slot=None):
        """
        Initializes a new object.  There are a few different valid ways of doing so:

        1) Pass in only nbtobj, as loaded from level.dat.  Everything will be populated
           from that one object.  Used on initial loads.

        2) Pass in other and slot, which is another InventorySlot object from which to
           copy all of our data.

        3) Only pass in "slot" - this will create an empty object.

        4) Pass in num, damage, count, and slot.
        """
        if nbtobj is None:
            if other is None:
                self.slot = slot
                self.num = num
                self.damage = damage
                self.count = count
                self.extratags = {}
                self.extratagtags = {}
                self.enchantments = []
            else:
                self.slot = other.slot
                self.num = other.num
                self.damage = other.damage
                self.count = other.count
                self.extratags = other.extratags
                self.extratagtags = other.extratagtags
                self.enchantments = []
                for ench in other.enchantments:
                    self.enchantments.append(ench.copy())
        else:
            self.num = nbtobj.value['id'].value
            self.damage = nbtobj.value['Damage'].value
            self.count = nbtobj.value['Count'].value
            self.slot = nbtobj.value['Slot'].value
            self.enchantments = []
            self.extratagtags = {}
            if 'tag' in nbtobj:
                if 'ench' in nbtobj.value['tag'].value:
                    for enchtag in nbtobj.value['tag'].value['ench'].value:
                        self.enchantments.append(EnchantmentSlot(nbtobj=enchtag))
                for tagname, value in nbtobj.value['tag'].value.iteritems():
                    if tagname not in ['ench']:
                        extratagtags[tagname] = value
            self.extratags = {}
            for tagname, value in nbtobj.value.iteritems():
                if tagname not in ['id', 'Damage', 'Count', 'Slot', 'tag']:
                    self.extratags[tagname] = value

        # Check to see if we're supposed to override the "slot" value
        if slot is not None:
            self.slot = slot

        # Doublecheck that we have some vars
        if self.extratags is None:
            self.extratags = {}
        if self.extratagtags is None:
            self.extratagtags = {}
        if self.enchantments is None:
            self.enchantments = []

    def __cmp__(self, other):
        """
        Comparator object for sorting
        """
        return cmp(self.num, other.num)

    def export_nbt(self):
        """
        Exports ourself as an NBT object
        """
        item_nbt = nbt.TAG_Compound()
        item_nbt['Count'] = nbt.TAG_Byte(self.count)
        item_nbt['Slot'] = nbt.TAG_Byte(self.slot)
        item_nbt['id'] = nbt.TAG_Short(self.num)
        item_nbt['Damage'] = nbt.TAG_Short(self.damage)
        for tagname, tagval in self.extratags.iteritems():
            item_nbt[tagname] = tagval
        if len(self.enchantments) > 0 or len(self.extratagtags) > 0:
            tag_nbt = nbt.TAG_Compound()
            if len(self.enchantments) > 0:
                ench_tag = nbt.TAG_List()
                for ench in self.enchantments:
                    ench_tag.append(ench.export_nbt())
                tag_nbt['ench'] = ench_tag
            for tagname, tagval in self.extratagtags.iteritems():
                tag_nbt[tagname] = tagval
            item_nbt['tag'] = tag_nbt
        return item_nbt

    def has_extra_info(self):
        """
        Returns whether or not we have any extra info in our tags
        """
        if len(self.extratags) > 0:
            return True
        if len(self.extratagtags) > 0:
            return True
        for ench in self.enchantments:
            if ench.has_extra_info():
                return True
        return False

class Inventory(object):
    """
    Holds Information about our inventory as a whole
    """

    def __init__(self, data):
        """
        Loads in memory fro the given NBT Object
        """
        self.inventory = {}
        for item in data:
            self._import_item(item)

    def _import_item(self, item):
        """
        Imports an item from the given NBT Object
        """
        slot = item.value['Slot'].value
        self.inventory[slot] = InventorySlot(nbtobj=item)

    def get_items(self):
        """
        Gets a list of all items in this inventory set
        """
        return self.inventory.values()

class InvDetails(gtk.Table):
    """
    Class to show our inventory item details
    """
    def __init__(self, parentwin, items, enchantments):
        super(InvDetails, self).__init__(3, 6)

        self.parentwin = parentwin
        self.items = items
        self.enchantments = enchantments
        self.button = None
        self.updating = True
        self.var_cache = {}

        cur_row = 0
        align = gtk.Alignment(.5, .5, 1, 1)
        align.set_padding(5, 5, 5, 5)
        label = gtk.Label()
        label.set_markup('<b>Inventory Slot Details</b>')
        align.add(label)
        self.attach(align, 0, 3, cur_row, cur_row+1, gtk.EXPAND|gtk.FILL, gtk.FILL)

        cur_row += 1
        self._rowlabel(cur_row, 'Slot Number')
        self._rowinfo(cur_row, 'slot')

        cur_row += 1
        self._rowlabel(cur_row, 'Item')
        self._rowinfo(cur_row, 'item')

        cur_row += 1
        self._rowlabel(cur_row, 'ID')
        self._rowspinner(cur_row, 'num', 0, 4095)

        cur_row += 1
        self._rowlabel(cur_row, 'Damage/Data')
        self._rowspinner(cur_row, 'damage', 0, 65535)
        self._rowextra(cur_row, 'damage_ext')

        cur_row += 1
        self._rowlabel(cur_row, 'Count')
        self._rowspinner(cur_row, 'count', 1, 255)
        self._rowextra(cur_row, 'count_ext')

        cur_row += 1
        self._rowlabel(cur_row, 'Enchantments', True)

        self.ench_vport = gtk.Viewport()
        self.ench_vport.set_shadow_type(gtk.SHADOW_IN)
        self.enchbox = gtk.Table(1, 1)
        align = gtk.Alignment(0, 0, 0, 0)
        align.set_padding(3, 3, 5, 0)
        align.add(self.enchbox)
        self.ench_vport.add(align)
        self.attach(self.ench_vport, 1, 3, cur_row, cur_row+1, gtk.FILL, gtk.FILL)

        cur_row += 1
        self.extrainfo = gtk.Label()
        self.attach(self.extrainfo, 0, 3, cur_row, cur_row+1, gtk.FILL, gtk.FILL)

    def _rowlabel(self, row, text, top=False):
        """
        A label on the given row
        """
        label = gtk.Label()
        label.set_markup('<b>%s:</b>' % (text))
        if top:
            align = gtk.Alignment(1, 0, 0, 0)
            align.set_padding(5, 0, 0, 0)
        else:
            align = gtk.Alignment(1, .5, 0, 0)
        align.add(label)
        self.attach(align, 0, 1, row, row+1, gtk.FILL, gtk.FILL)

    def _rowinfo(self, row, var):
        """
        Adds an informative info field
        """
        label = gtk.Label()
        self.var_cache[var] = label
        align = gtk.Alignment(0, .5, 0, 0)
        align.set_padding(3, 3, 5, 0)
        align.add(label)
        self.attach(align, 1, 3, row, row+1, gtk.FILL, gtk.FILL)

    def _rowspinner(self, row, var, val_min, val_max):
        """
        Adds a spinner to the given row
        """
        align = gtk.Alignment(0, .5, 0, 0)
        align.set_padding(3, 3, 5, 0)
        adjust = gtk.Adjustment(0, val_min, val_max, 1, 1)
        spinner = gtk.SpinButton(adjust)
        self.var_cache[var] = spinner
        align.add(spinner)
        self.attach(align, 1, 2, row, row+1, gtk.FILL, gtk.FILL)
        spinner.connect('value-changed', self.new_values)

    def _rowextra(self, row, var):
        """
        An extra gtk.Label to put after our data value
        """
        align = gtk.Alignment(0, .5, 0, 0)
        align.set_padding(3, 3, 5, 0)
        label = gtk.Label()
        self.var_cache[var] = label
        align.add(label)
        self.attach(align, 2, 3, row, row+1, gtk.EXPAND|gtk.FILL, gtk.FILL)

    def _get_var(self, var):
        """
        Returns a GTK Widget from our var cache
        """
        if var in self.var_cache:
            return self.var_cache[var]
        else:
            return None

    def update_from_button(self, button):
        """
        Updates all our information given a button
        """
        self.button = button
        self._update_info()

    def _update_info(self):
        """
        Updates all our information with our loaded button
        """
        self.updating = True
        self._get_var('slot').set_text('%d' % (self.button.slot))
        if self.button.inventoryslot is None:
            self._get_var('item').set_markup('<i>No Item</i>')
            self._get_var('num').set_value(0)
            self._get_var('damage').set_value(0)
            self._get_var('damage_ext').set_text('')
            self._get_var('count').set_value(1)
            self._get_var('count_ext').set_text('')
            self._get_var('damage').set_sensitive(False)
            self._get_var('count').set_sensitive(False)
            self.extrainfo.set_text('')
            self.ench_vport.set_visible(False)
        else:
            self._get_var('damage').set_sensitive(True)
            self._get_var('count').set_sensitive(True)
            self._get_var('num').set_value(self.button.inventoryslot.num)
            self._get_var('damage').set_value(self.button.inventoryslot.damage)
            self._get_var('count').set_value(self.button.inventoryslot.count)
            item = self.items.get_item(self.button.inventoryslot.num, self.button.inventoryslot.damage)
            if item:
                self._get_var('item').set_text(item.name)
                self._get_var('count_ext').set_markup('<i>(maximum quanity: %d)</i>' % (item.max_quantity))
                if item.max_damage is None:
                    self._get_var('damage_ext').set_text('')
                else:
                    self._get_var('damage_ext').set_markup('<i>(maximum damage: %d)</i>' % (item.max_damage))
            else:
                self._get_var('item').set_markup('<i>Unknown Item</i>')
                self._get_var('damage_ext').set_text('')
                self._get_var('count_ext').set_text('')
            if self.button.inventoryslot.has_extra_info():
                self.extrainfo.set_markup('<i>Contains extra tag info</i>')
            else:
                self.extrainfo.set_text('')

            # Enchantments
            for contents in self.enchbox.get_children():
                self.enchbox.remove(contents)
            self.enchbox.resize(3, len(self.button.inventoryslot.enchantments)+1)
            last_idx = -1
            for idx, ench in enumerate(self.button.inventoryslot.enchantments):

                # First the enchantment text itself
                ench_text = self.enchantments.get_text(ench.num, ench.lvl)
                if ench.has_extra_info():
                    ench_text = '%s <i>(has extra tag info)</i>' % (ench_text)
                align = gtk.Alignment(0, .5, 0, 0)
                align.set_padding(0, 0, 0, 5)
                label = gtk.Label()
                label.set_markup(ench_text)
                align.add(label)
                self.enchbox.attach(align, 0, 1, idx, idx+1, gtk.FILL, gtk.FILL)
                
                # If we're not at (or above) the enchantment's max value, a button to do that
                ench_obj = self.enchantments.get_by_id(ench.num)
                if ench_obj is not None:
                    if ench.lvl < ench_obj.max_power:
                        button = gtk.Button()
                        button.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_UP, gtk.ICON_SIZE_MENU))
                        button.set_tooltip_text('Maximize Enchantment Level')
                        button.connect('clicked', self.ench_max_level, idx)
                        self.enchbox.attach(button, 1, 2, idx, idx+1, gtk.FILL, gtk.FILL)
                
                # And a button to delete
                button = gtk.Button()
                button.set_image(gtk.image_new_from_stock(gtk.STOCK_CUT, gtk.ICON_SIZE_MENU))
                button.set_tooltip_text('Delete Enchantment')
                button.connect('clicked', self.ench_delete, idx)
                self.enchbox.attach(button, 2, 3, idx, idx+1, gtk.FILL, gtk.FILL)

                last_idx = idx

            # Now the enchantment Add button
            button = gtk.Button()
            button.set_image(gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU))
            button.set_tooltip_text('Add new enchantment to this item')
            button.connect('clicked', self.add_enchantment)
            align = gtk.Alignment(0, 0, 1, 0)
            align.add(button)
            self.enchbox.attach(align, 0, 1, last_idx+1, last_idx+2, 0, gtk.FILL)


            # If we have at least one enchantment, draw a border
            if len(self.button.inventoryslot.enchantments) > 0:
                self.ench_vport.set_shadow_type(gtk.SHADOW_IN)
            else:
                self.ench_vport.set_shadow_type(gtk.SHADOW_NONE)

            # Show everything
            self.ench_vport.set_visible(True)
            self.ench_vport.show_all()

        self.updating = False

    def new_values(self, button, param=None):
        """
        One of our user-settable values has changed.  Update our button's inventory slot
        """
        if self.updating:
            return

        if self.button is None:
            print 'Error: no button'
            return

        if self.button.inventoryslot is None:
            self.button.add_item()

        if self._get_var('num').get_value() == 0:
            self.button.clear_item()
        else:
            self.button.inventoryslot.num = self._get_var('num').get_value()
            self.button.inventoryslot.damage = self._get_var('damage').get_value()
            self.button.inventoryslot.count = self._get_var('count').get_value()
        self._update_info()
        self.button.update_graphics()

        # Update our Undo object
        global undo
        undo.change()

    def add_enchantment(self, button, param=None):
        """
        Adds a new enchantment to this window
        """
        dialog = dialogs.NewEnchantmentDialog(self.parentwin, self, self.button.inventoryslot, self.items, self.enchantments)
        resp = dialog.run()
        new_num = dialog.ench_id.get_value()
        new_lvl = dialog.ench_lvl.get_value()
        dialog.destroy()
        if resp == gtk.RESPONSE_OK:
            if new_num >= 0 and new_lvl >= 0:
                if self.button.inventoryslot is not None:
                    slot = EnchantmentSlot(num=new_num, lvl=new_lvl)
                    self.button.inventoryslot.enchantments.append(slot)
                    self._update_info()
                    self.button.update_graphics()
                    global undo
                    undo.change()

    def ench_max_level(self, button, index):
        """
        Brings an enchantment up to its maximum level
        """
        if self.button.inventoryslot is not None:
            if index < len(self.button.inventoryslot.enchantments):
                ench_slot = self.button.inventoryslot.enchantments[index]
                ench = self.enchantments.get_by_id(ench_slot.num)
                if ench:
                    if ench_slot.lvl != ench.max_power:
                        ench_slot.lvl = ench.max_power
                        self._update_info()
                        global undo
                        undo.change()

    def ench_delete(self, button, index):
        """
        Deletes the given enchantment
        """
        if self.button.inventoryslot is not None:
            if index < len(self.button.inventoryslot.enchantments):
                self.button.inventoryslot.enchantments.pop(index)
                self._update_info()
                self.button.update_graphics()
                global undo
                undo.change()

class InvImage(gtk.DrawingArea):
    """
    Class to show an image inside one of our inventory slot buttons.
    This is actually a DrawingArea which uses Cairo to do all the lower-level
    rendering stuff.

    Note that rather than render directly to the window immediately, we
    cache our own ImageSurface and then draw to the window at the end.  This
    might possibly be more efficient, but we're actually doing it that way
    because that way we can easily copy the image data when doing drag-and-
    drop, to set the drag icon.  We can't just call get_target() on the
    context returned from self.window.cairo_create() because that surface
    is an XlibSurface, which apparently contains the entire app window, not
    just our one widget.
    """

    # Our size
    size = 50

    # Corner constants
    CORNER_NW = 0
    CORNER_NE = 1
    CORNER_SE = 2
    CORNER_SW = 3
    CORNER_CENTER = 4

    # Damage bar constants
    DAMAGE_X = 3
    DAMAGE_Y = size-6
    DAMAGE_W = size-6
    DAMAGE_H = 3

    # We define our own expose behavior
    __gsignals__ = { 'expose_event': 'override' }

    def __init__(self, button, empty=None):
        super(InvImage, self).__init__()
        self.set_size_request(self.size, self.size)
        self.button = button
        self.surf = None
        self.cr = None
        self.pangoctx = None
        self.cairoctx = None
        self.empty = empty

    def do_expose_event(self, event):
        """
        On our first expose event we'll set up some various vars
        which we can't set up until the window's exposed.  Then
        just call the main draw() function.
        """
        # TODO: huh, something in here needs to be generated each time.
        if True or self.cr is None:
            self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.size, self.size)
            self.cr = cairo.Context(self.surf)
            self.pangoctx = self.get_parent().get_pango_context()
            self.pangolayout = pango.Layout(self.pangoctx)
            self.pangolayout.set_font_description(pango.FontDescription('sans bold 9'))
            self.pangolayout.set_width(self.size)
            self.pangolayoutbigger = pango.Layout(self.pangoctx)
            self.pangolayoutbigger.set_font_description(pango.FontDescription('sans bold 12'))
            self.pangolayoutbigger.set_width(self.size)
            self.cairoctx = pangocairo.CairoContext(self.cr)
        self.draw()

    def draw(self):
        """
        The meat of the rendering
        """
        slotinfo = self.button.inventoryslot

        done_bg = False
        if self.button.get_active():
            done_bg = True
            self.cr.set_source_rgba(.8, .8, .8, 1)
            self.cr.rectangle(0, 0, self.size, self.size)
            self.cr.fill()

        if slotinfo is None:
            # Nothing in this inventory slot
            if self.empty is None:
                if not done_bg:
                    self.cr.set_source_rgba(0, 0, 0, 0)
                    self.cr.rectangle(0, 0, self.size, self.size)
                    self.cr.fill()
            else:
                self._surface_center(self.empty)
        else:
            # Get information about the item, if we can
            imgsurf = None
            item = self.button.items.get_item(slotinfo.num, slotinfo.damage)
            if item is not None:
                imgsurf = item.get_image(True)

            # Now get the "base" image
            if imgsurf is None:
                center = self.size/2

                self.cr.set_source_rgba(0, 0, 0, 1)
                self.cr.arc(center, center, center-10, 0, math.pi*2)
                self.cr.fill()

                self.cr.set_source_rgba(1, 1, 1, 1)
                self.cr.arc(center, center, center-12, 0, math.pi*2)
                self.cr.fill()

                self.cr.set_source_rgba(.4196, .596, .7725, 1)
                self.cr.arc(center, center, center-14, 0, math.pi*2)
                self.cr.fill()

                self._text_at('%d' % (slotinfo.num), [1, 1, 1, 1], [0, 0, 0, 1], self.CORNER_CENTER)
            else:
                self._surface_center(imgsurf)

            # Now the quantity
            if slotinfo.count > 1:
                if item is None:
                    max_quantity = 64
                else:
                    max_quantity = item.max_quantity

                if slotinfo.count <= max_quantity:
                    outlinecolor = [0, 0, 0, 1]
                else:
                    outlinecolor = [1, 0, 0, 1]

                self._text_at('%d' % (slotinfo.count), [1, 1, 1, 1], outlinecolor, self.CORNER_SE)

            # Damage (either bar or number)
            if item is not None and item.all_data:
                # Report on data value, but it's not an error
                self._text_at('%d' % (slotinfo.damage), [.2, .2, 1, 1], [1, 1, 1, 1], self.CORNER_NW)
            elif slotinfo.damage > 0:
                if item is None:
                    # No item data to compare against, assume that it's wrong, I guess
                    self._text_at('%d' % (slotinfo.damage), [1, 0, 0, 1], [0, 0, 0, 1], self.CORNER_NW)
                elif item.max_damage is None:
                    # No max damage defined, so check for the Unique ID to see if we're a known data
                    # type or not.
                    if item.data != slotinfo.damage:
                        # Invalid data, apparently!  Red text.
                        self._text_at('%d' % (slotinfo.damage), [1, 0, 0, 1], [0, 0, 0, 1], self.CORNER_NW)
                else:
                    # We have a max damage definition; check against it
                    if (slotinfo.damage > item.max_damage):
                        # Damage value is over our known max
                        self._text_at('%d' % (slotinfo.damage), [1, 0, 0, 1], [0, 0, 0, 1], self.CORNER_NW)
                    else:
                        # Damage is in the proper range - draw a damage bar
                        percent = 1 - (slotinfo.damage / float(item.max_damage))

                        # The base (black) bar
                        self.cr.set_source_rgba(0, 0, 0, 1)
                        self.cr.rectangle(self.DAMAGE_X, self.DAMAGE_Y, self.DAMAGE_W, self.DAMAGE_H)
                        self.cr.fill()

                        # The actual damage notifier
                        self.cr.set_source_rgba(1-percent, percent, 0, 1)
                        self.cr.rectangle(self.DAMAGE_X, self.DAMAGE_Y, self.DAMAGE_W*percent, self.DAMAGE_H)
                        self.cr.fill()

            # Enchantments
            if len(slotinfo.enchantments) > 0:
                self._text_at('+%d' % (len(slotinfo.enchantments)), [.7764, .1686, 1, 1], [0, 0, 0, 1], self.CORNER_NE)

            # Extra tag info
            if slotinfo.has_extra_info():
                self._text_at('+', [0, 1, 0, 1], [0, 0, 0, 1], self.CORNER_SW, True)

        # Finally, at the very end, copy our stored ImageSurface to our
        # actual DrawingArea window
        wincr = self.window.cairo_create()
        wincr.set_source_surface(self.surf)
        wincr.rectangle(0, 0, self.size, self.size)
        wincr.fill()

    def _surface_center(self, surface):
        """
        Draws a cairo surface to the center of the image.
        """
        offset = (self.size - surface.get_width()) / 2
        self.cr.set_source_surface(surface, offset, offset)
        self.cr.move_to(0, 0)
        self.cr.rectangle(offset, offset, surface.get_width(), surface.get_width())
        self.cr.fill()

    def _text_at(self, text, textcolor, outlinecolor, corner, bigger=False):
        """
        Draws some text to our surface at the given location, using the given colors
        for the text and the outline.
        """
        if bigger:
            layout = self.pangolayoutbigger
        else:
            layout = self.pangolayout
        layout.set_markup(text)
        (width, height) = map(lambda x: x/pango.SCALE, layout.get_size())
        if corner == self.CORNER_NW:
            x = 1
            y = 1
        elif corner == self.CORNER_NE:
            x = self.size-1-width
            y = 1
        elif corner == self.CORNER_SE:
            x = self.size-1-width
            y = self.size-1-height
        elif corner == self.CORNER_SW:
            x = 1
            y = self.size-1-height
        else:
            x = (self.size-width)/2
            y = (self.size-height)/2

        # Now the actual rendering
        self.cr.move_to(x, y)
        self.cairoctx.layout_path(layout)
        self.cr.set_source_rgba(*outlinecolor)
        self.cr.set_line_width(2)
        self.cr.stroke()
        self.cr.move_to(x, y)
        self.cr.set_source_rgba(*textcolor)
        self.cairoctx.show_layout(layout)

    def update(self):
        """
        Re-queue an update for ourselves
        """
        if self.window is not None:
            self.window.invalidate_rect(gtk.gdk.Rectangle(0, 0, self.size, self.size), True)
            self.window.process_updates(True)

    def get_pixbuf(self):
        """
        Returns our currently-displayed image as a gtk.gdk.Pixbuf
        """
        return get_pixbuf_from_surface(self.surf)

class TrashButton(gtk.Button):
    """
    Class for our trash button
    """

    def __init__(self, surf):
        super(TrashButton, self).__init__()
        self.set_size_request(63, 63)
        self.set_border_width(0)
        self.set_relief(gtk.RELIEF_HALF)
        self.image = gtk.Image()
        self.image.set_from_pixbuf(get_pixbuf_from_surface(surf))
        self.add(self.image)
        self.set_tooltip_markup('Trash <i>(Drag items here to delete)</i>')

        # Set up drag and drop inbetween items
        target = [ ('', 0, 0) ]
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP, target, gtk.gdk.ACTION_COPY)
        self.connect('drag_drop', self.target_drag_drop)
        self.connect('drag_motion', self.target_drag_motion)

    def target_drag_drop(self, img, context, x, y, time):
        """
        What to do when we've received a drag request.  (ie: delete the data)
        """
        other = context.get_source_widget()
        try:
            other.clear_item()
        except AttributeError:
            # Drag came from the selection list
            return

        if other.get_active():
            other.update_item()
        else:
            other.update_graphics()

        # Update our Undo object
        global undo
        undo.change()

    def target_drag_motion(self, img, context, x, y, time):
        context.drag_status(context.suggested_action, time)
        return True

class InvButton(gtk.RadioButton):
    """
    Class for an individual button on our inventory screen
    """

    def __init__(self, slot, items, enchantments, detail, empty=None):
        super(InvButton, self).__init__()
        self.set_mode(False)
        # TODO: Get the button size down properly
        self.set_size_request(63, 63)
        self.set_border_width(0)
        self.set_relief(gtk.RELIEF_HALF)
        self.set_active(False)
        self.slot = slot
        self.items = items
        self.enchantments = enchantments
        self.detail = detail
        self.inventoryslot = None
        self.image = InvImage(self, empty)
        self.add(self.image)
        self.connect('clicked', self.on_clicked)
        self.connect('button-release-event', self.on_mouse)

        # Set up drag and drop inbetween items
        target = [ ('', 0, 0) ]
        self.drag_source_set(gtk.gdk.BUTTON1_MASK, target, gtk.gdk.ACTION_COPY)
        self.connect('drag_begin', self.drag_begin)
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP, target, gtk.gdk.ACTION_COPY)
        self.connect('drag_drop', self.target_drag_drop)
        self.connect('drag_motion', self.target_drag_motion)

    def drag_begin(self, widget, context):
        self.drag_source_set_icon_pixbuf(self.image.get_pixbuf())

    def target_drag_drop(self, img, context, x, y, time):
        """
        What to do when we've received a drag request.  (Mostly just: copy the data)
        """
        other = context.get_source_widget()
        try:
            # Our dragged object is a fellow InvButton
            if other.inventoryslot is None:
                self.inventoryslot = None
            else:
                self.inventoryslot = InventorySlot(other=other.inventoryslot, slot=self.slot)
        except AttributeError:
            # Our dragged object is a raw Item
            if other.get_selected_item() is not None:
                self.inventoryslot = other.get_selected_item().get_new_inventoryslot(self.slot)

        # Update our graphics and potentially the details area
        if self.get_active():
            self.update_item()
        else:
            self.update_graphics()

        # Update our Undo object
        global undo
        undo.change()

    def get_text(self):
        """
        Gets a textual representation of this inventory slot
        """
        slot = self.inventoryslot
        if slot is not None:
            if slot.num > 0:
                item = self.items.get_item(slot.num, slot.damage)
                if item is None:
                    if slot.damage > 0:
                        name = 'Unknown Item %d, %d damage' % (slot.num, slot.damage)
                    else:
                        name = 'Unknown Item %d' % (slot.num)
                else:
                    if item.max_damage is not None and slot.damage > 0:
                        percent = int(100*(slot.damage / float(item.max_damage)))
                        name = '%s, %d%% damaged' % (item.name, percent)
                    elif item.all_data:
                        name = '%s %d' % (item.name, slot.damage)
                    else:
                        name = item.name
                if slot.count > 1:
                    prefix = '%dx ' % (slot.count)
                else:
                    prefix = ''
                if len(slot.extratags) > 0:
                    suffix = ' (has extra tag info)'
                else:
                    suffix = ''
                lines = []
                lines.append('%s%s%s' % (prefix, name, suffix))
                for ench in slot.enchantments:
                    lines.append(self.enchantments.get_text(ench.num, ench.lvl))
                return "\n".join(lines)
            else:
                return None
        else:
            return None

    def target_drag_motion(self, img, context, x, y, time):
        context.drag_status(context.suggested_action, time)
        return True

    def add_item(self):
        """
        Adds a blank item to this button; used when creating an item via the details
        area.
        """
        self.inventoryslot = InventorySlot(slot=self.slot)

    def clear_item(self):
        """
        Gets rid of our InventorySlot object.  Used when deleting an item via the
        details area.
        """
        self.inventoryslot = None

    def clear(self):
        """
        Clears out our stored inventory slot
        """
        self.inventoryslot = None
        self.update_graphics()

    def update_slot(self, inventoryslot):
        """
        Updates this button with new inventoryslot information
        """
        self.inventoryslot = inventoryslot
        self.update_graphics()

    def update_graphics(self):
        """
        There have been changes to our object, update the graphics
        """
        self.image.update()
        text = self.get_text()
        if text is None:
            self.set_has_tooltip(False)
        else:
            self.set_tooltip_text(text)
            self.set_has_tooltip(True)

    def on_clicked(self, button, params=None):
        """
        What to do when we're clicked
        """
        self.update_item()

    def update_item(self):
        """
        Refreshes both our button graphic, and the detail window (if appropriate)
        """
        self.update_graphics()
        if self.get_active():
            self.detail.update_from_button(self)

    def on_mouse(self, widget, event):
        """
        Process a mouse click (other than our "main" mouse click, which
        will trigger the on_clicked action.
        """
        if event.button == 3:
            self.set_active(True)
            # Right-click, fill stack or repair damage
            repaired = self.repair()
            filled = self.fill()
            if repaired or filled:
                self.update_item()

    def repair(self):
        """
        Repairs our item, if we're the sort of item which can be
        repaired.  Returns True if we actually performed a repair, and
        False otherwise
        """
        if self.inventoryslot is not None:
            item = self.items.get_item(self.inventoryslot.num, self.inventoryslot.damage)
            if item is not None:
                if item.max_damage is not None:
                    if self.inventoryslot.damage != 0:
                        self.inventoryslot.damage = 0
                        global undo
                        undo.change()
                        return True
        return False

    def fill(self):
        """
        Fills our item to maximum capacity.  Returns True if we actually
        performed the fill, and False otherwise.
        """
        if self.inventoryslot is not None:
            item = self.items.get_item(self.inventoryslot.num, self.inventoryslot.damage)
            if item is not None:
                if self.inventoryslot.count < item.max_quantity:
                    self.inventoryslot.count = item.max_quantity
                    global undo
                    undo.change()
                    return True
        return False

    def max_ench(self):
        """
        Brings all our existing enchantments up to maximum level.  Returns true
        or false depending on if any data was actually changed.
        """
        updated = False
        if self.inventoryslot is not None:
            for ench in self.inventoryslot.enchantments:
                ench_obj = self.enchantments.get_by_id(ench.num)
                if ench_obj:
                    if ench.lvl < ench_obj.max_power:
                        updated = True
                        ench.lvl = ench_obj.max_power
        if updated:
            global undo
            undo.change()
        return updated

    def enchant_all(self):
        """
        Give our item all available enchantments, and incidentally bring them
        all up to max level if they're not already.  Returns true or false
        depending on if any data was actually changed.
        """
        updated = False
        if self.inventoryslot is not None:
            existing_enchantments = []
            for ench in self.inventoryslot.enchantments:
                existing_enchantments.append(ench.num)
            item = self.items.get_item(self.inventoryslot.num, self.inventoryslot.damage)
            if item:
                to_add = []
                for ench_obj in item.enchantments:
                    if ench_obj.num not in existing_enchantments:
                        to_add.append(EnchantmentSlot(num=ench_obj.num, lvl=ench_obj.max_power))
                        updated = True
                for ench_slot in to_add:
                    self.inventoryslot.enchantments.append(ench_slot)
        if self.max_ench():
            updated = True
        if updated:
            global undo
            undo.change()
        return updated

class BaseInvTable(gtk.Table):
    """
    The class from which our inventory tables derive
    """

    def __init__(self, rows, cols, items, enchantments, detail, gui_sheet):
        super(BaseInvTable, self).__init__(rows, cols)

        self.buttons = {}
        self.group = None
        self.items = items
        self.enchantments = enchantments
        self.detail = detail

        # Trash button
        self.attach(TrashButton(gui_sheet.get_tex(1, 0, True)), 8, 9, 0, 1, gtk.FILL, gtk.FILL, ypadding=7)

    def _new_button(self, x, y, slot, ypadding=0, empty=None):
        """
        Adds a new button at the specified coordinates, representing the specified
        inventory slot.
        """
        if slot in self.buttons:
            raise Exception("Inventory slot %d already exists" % (slot))
        button = InvButton(slot, self.items, self.enchantments, self.detail, empty)
        if self.group is None:
            self.group = button
        else:
            button.set_group(self.group)
        self.buttons[slot] = button
        self.attach(button, x, x+1, y, y+1, gtk.FILL, gtk.FILL, ypadding=ypadding)

    def clear_buttons(self):
        """
        Removes all data from our buttons
        """
        for button in self.buttons.values():
            button.clear()

    def update_active_button(self):
        """
        Loops through all our buttons and makes sure that the proper one is
        set as the fully-active button.
        """
        for button in self.buttons.values():
            if button.get_active():
                button.update_item()
                break

    def repair_all(self):
        """
        Repairs all items
        """
        for button in self.buttons.values():
            if button.repair():
                button.update_item()

    def fill_all(self):
        """
        Fills all items
        """
        for button in self.buttons.values():
            if button.fill():
                button.update_item()

    def enchant_all(self):
        """
        Enchants all items with all possible enchantments
        """
        for button in self.buttons.values():
            if button.enchant_all():
                button.update_item()

    def max_ench(self):
        """
        Brings all existing enchantments up to their maximum levels
        """
        for button in self.buttons.values():
            if button.max_ench():
                button.update_item()

    def export_nbt(self):
        """
        Exports our current items to a new NBT Tag_Compound
        """
        inv_list = []
        slots = []
        for button in self.buttons.values():
            if button.inventoryslot is not None:
                slots.append(button.inventoryslot)
        slots.sort()
        for slot in slots:
            inv_list.append(slot.export_nbt())
        return inv_list

class InvTable(BaseInvTable):
    """
    Table to store our basic inventory info that we know about For Sure
    """

    def __init__(self, items, enchantments, detail, gui_sheet):
        super(InvTable, self).__init__(5, 9, items, enchantments, detail, gui_sheet)

        # Armor slots
        self._new_button(0, 0, 103, 7, empty=gui_sheet.get_tex(0, 0, True))
        self._new_button(1, 0, 102, 7, empty=gui_sheet.get_tex(0, 1, True))
        self._new_button(2, 0, 101, 7, empty=gui_sheet.get_tex(0, 2, True))
        self._new_button(3, 0, 100, 7, empty=gui_sheet.get_tex(0, 3, True))

        # Ordinary inventory slots
        for i in range(9):
            self._new_button(i, 1, 9+i)
            self._new_button(i, 2, 18+i)
            self._new_button(i, 3, 27+i)
            self._new_button(i, 4, i, 7)
        
        # Make sure that all is well here
        self.update_active_button()

    def populate_from(self, inventory):
        """
        Populates all of our buttons from the given inventory object.  Returns
        any extra inventory slots that this object doesn't cover.
        """
        extra_items = []
        self.clear_buttons()
        for item in inventory.get_items():
            if item.slot in self.buttons:
                self.buttons[item.slot].update_slot(item)
            else:
                extra_items.append(item)
        self.update_active_button()
        return extra_items

class ExtraInvTable(BaseInvTable):
    """
    Table to store extra inventory slots which the main InvTable doesn't
    support.  (So basically this is just to support mods, or possibly
    much earlier versions of Minecraft which would let you store items
    in your 2x2 crafting area, etc.)
    """

    button_cols = 9

    def __init__(self, items, enchantments, detail, gui_sheet):
        """
        There's very little to do here, since all our contents are
        created dynamically via populate_from()
        """
        super(ExtraInvTable, self).__init__(9, 1, items, enchantments, detail, gui_sheet)

    def populate_from(self, items):
        """
        Populates from a list of "extra" items that need to be stored
        and displayed somewhere.
        """
        
        # First, totally clear out anything which might be in here
        # Note that this will leave the Trash icon alone
        self.clear_buttons()
        for button in self.buttons.values():
            self.remove(button)
        self.buttons = {}
        self.group = None

        # Start anew!
        if len(items) > 0:
            # Figure out how many rows we'll have.
            rows = len(items)/self.button_cols
            if (len(items) % self.button_cols) > 0:
                rows += 1
            rows += 1
            self.resize(9, rows)

            # And now go and create our bunch of buttons, and load in the
            # items
            cur_x = 0
            cur_y = 1
            for item in items:
                self._new_button(cur_x, cur_y, item.slot)
                self.buttons[item.slot].update_slot(item)
                cur_x += 1
                if cur_x == self.button_cols:
                    cur_x = 0
                    cur_y += 1
            self.update_active_button()

            # Make sure things are visible
            self.show_all()

class ItemView(gtk.TreeView):
    """
    TreeView class to actually store all the items
    """

    ( COL_ICON, COL_NAME, COL_OBJ, COL_VISIBLE ) = range(4)

    def __init__(self, items):

        self.items = items
        self.filtergroup = None
        self.text = None
        self.filter_by_group = False
        self.filter_by_text = False
        self.items_visible = True;

        self.model = gtk.ListStore(gtk.gdk.Pixbuf, str, object, bool)
        for item in self.items.get_items():
            iteritem = self.model.append()
            self.model.set(iteritem,
                    self.COL_ICON, item.get_pixbuf(),
                    self.COL_NAME, item.name,
                    self.COL_OBJ, item,
                    self.COL_VISIBLE, not item.unknown)

        self.filterobj = self.model.filter_new()
        self.filterobj.set_visible_column(self.COL_VISIBLE)

        super(ItemView, self).__init__(self.filterobj)

        self.set_rules_hint(False)
        self.set_search_column(self.COL_NAME)
        self.set_headers_visible(False)

        column = gtk.TreeViewColumn('Icon', gtk.CellRendererPixbuf(), pixbuf=self.COL_ICON)
        self.append_column(column)

        column = gtk.TreeViewColumn('Name', gtk.CellRendererText(), text=self.COL_NAME)
        self.append_column(column)

        # Set up drag-and-drop
        self.enable_drag_n_drop()
        self.connect('drag_begin', self.drag_begin)

    def enable_drag_n_drop(self):
        """
        Turns drag-and-drop on
        """
        self.drag_source_set(gtk.gdk.BUTTON1_MASK, [ ('', 0, 0) ], gtk.gdk.ACTION_COPY)

    def disable_drag_n_drop(self):
        """
        Turns drag-and-drop off
        """
        self.drag_source_unset()

    def get_selected_item(self):
        """
        Returns the Item that's currently selected
        """
        selection = self.get_selection()
        model, iteritem = selection.get_selected()
        if iteritem is None:
            return None
        else:
            return model.get_value(iteritem, self.COL_OBJ)

    def drag_begin(self, widget, context):
        """
        Change our drag icon when we start dragging
        """
        item = widget.get_selected_item()
        if item is None:
            self.drag_source_set_icon_stock(gtk.STOCK_DIALOG_ERROR)
        else:
            self.drag_source_set_icon_pixbuf(get_pixbuf_from_surface(item.get_image(True)))

    def filter_text(self, text):
        """
        Filter our list of items based on the given text
        """
        if text is None or text == '':
            self.filter_by_text = False
            self.text = ''
        else:
            self.filter_by_text = True
            self.text = text.lower()
        self.apply_filters()

    def filter_group(self, group):
        """
        Sets our filter group
        """
        self.filtergroup = group
        if group is None:
            self.filter_by_group = False
        else:
            self.filter_by_group = True
        self.apply_filters()

    def apply_filters(self):
        """
        Applies any active filters that we have.
        """
        found_active = False
        unknown_row = None
        unknown_item = None
        for row in self.model:
            item = row[self.COL_OBJ]
            if item.unknown:
                unknown_row = row
                unknown_item = item
            if self.filter_by_group:
                if self.filtergroup not in item.groups:
                    row[self.COL_VISIBLE] = False
                    continue
            if self.filter_by_text:
                if self.text not in row[self.COL_NAME].lower():
                    if not self.text.isdigit() or int(self.text) != item.num:
                        row[self.COL_VISIBLE] = False
                        continue
            if item.unknown:
                row[self.COL_VISIBLE] = False
            else:
                row[self.COL_VISIBLE] = True
                found_active = True

        if found_active and not self.items_visible:
            self.items_visible = True
            self.enable_drag_n_drop()
        elif not found_active and self.items_visible:
            if self.filter_by_text and self.text.isdigit():
                # Substitute our fake "Unknown" item
                num = int(self.text)
                if num > 65535:
                    num = 65535
                unknown_item.num = num
                unknown_row[self.COL_NAME] = 'Unknown Item %d' % (num)
                unknown_row[self.COL_VISIBLE] = True
            else:
                self.items_visible = False
                self.disable_drag_n_drop()

class ItemScroll(gtk.ScrolledWindow):
    """
    Class that holds our list of items to choose from
    """

    ( COL_ICON, COL_NAME ) = range(2)

    def __init__(self, items):
        super(ItemScroll, self).__init__()

        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self.tv = ItemView(items)
        self.add(self.tv)

    def filter_text(self, text):
        """
        Filter our list of items based on the given text
        """
        self.tv.filter_text(text)
        # TODO: why doesn't this adjustment work?
        self.get_vadjustment().set_value(0)

    def filter_group(self, group):
        """
        Filter our list of items based on the given text
        """
        self.tv.filter_group(group)
        # TODO: why doesn't this adjustment work?
        self.get_vadjustment().set_value(0)

class SearchEntry(gtk.Entry):
    """
    Class of our Entry box for searching our item list
    """

    def __init__(self, parentobj):
        super(SearchEntry, self).__init__()
        self.parentobj = parentobj
        self.changing = False
        self.empty = False

        # Technically grabbing these right now and storing them isn't
        # a good idea, because the user could change themes while we're
        # running.  Whatever.
        self.color_inactive = self.style.text[gtk.STATE_INSENSITIVE]
        self.color_active = self.style.text[gtk.STATE_NORMAL]

        self.set_empty()
        self.connect('changed', self.on_changed)
        self.connect('focus-in-event', self.on_focus_in)
        self.connect('focus-out-event', self.on_focus_out)

    def set_empty(self):
        """
        Sets ourselves to be "empty," which actually means
        that we're going to have a greyed-out "search" text
        in there
        """
        self.changing = True
        font = pango.FontDescription()
        font.set_style(pango.STYLE_ITALIC)
        self.modify_font(font)
        self.modify_text(gtk.STATE_NORMAL, self.color_inactive)
        self.set_text('Type to Search Items...')
        self.empty = True
        self.changing = False

    def set_active(self):
        """
        Sets ourselves to be "active" - ie: ready for user
        input.
        """
        self.changing = True
        font = pango.FontDescription()
        font.set_style(pango.STYLE_NORMAL)
        self.modify_font(font)
        self.modify_text(gtk.STATE_NORMAL, self.color_active)
        self.set_text('')
        self.empty = False
        self.changing = False

    def on_changed(self, widget, param=None):
        """
        What to do when our input has been changed
        """
        if not self.changing:
            self.parentobj.update_scroll(self)

    def on_focus_in(self, widget, event, param=None):
        """
        Focus-in event
        """
        if self.empty:
            self.set_active()

    def on_focus_out(self, widget, event, param=None):
        """
        Focus-out event
        """
        if self.get_text_length() == 0:
            self.set_empty()

class ItemSelector(gtk.VBox):
    """
    Class to show our item selection
    """

    def __init__(self, items, groups):
        super(ItemSelector, self).__init__()

        self.entry = SearchEntry(self)
        self.pack_start(self.entry, False, True)

        self.itemscroll = ItemScroll(items)
        self.pack_start(self.itemscroll, True, True)

        self.grouptable = GroupTable(groups, self)
        align = gtk.Alignment(1, 0, 1, 0)
        align.add(self.grouptable)
        self.pack_start(align, False, True)
        
        self.filtergroup = None

    def update_scroll(self, widget, param=None):
        """
        Our entry text has changed; filter our list.
        """
        self.itemscroll.filter_text(widget.get_text())

    def filter_group(self, group):
        """
        Apply a group of icons as a filter to our list
        """
        self.itemscroll.filter_group(group)

class GroupButton(gtk.ToggleButton):
    """
    Class for an individual button in our Group-selection area
    """

    def __init__(self, table, group):
        super(GroupButton, self).__init__()
        self.set_mode(False)
        self.set_border_width(0)
        self.set_relief(gtk.RELIEF_HALF)
        self.set_active(False)
        self.group = group
        self.table = table
        self.set_tooltip_text(group.name)
        image = gtk.image_new_from_pixbuf(group.get_pixbuf())
        self.add(image)
        self.connect('clicked', self.on_clicked)

    def on_clicked(self, button):
        """
        Process a click
        """
        if self.get_active():
            self.set_active(True)
            self.table.notify_clicked(button)
        else:
            self.set_active(False)
            self.table.notify_unclicked()

class GroupTable(gtk.Table):
    """
    Table of Group icons which can be used to filter our
    selection of items
    """

    cols = 10

    def __init__(self, groups, selector):

        self.selector = selector
        self.buttons = []

        # Figure out how many rows we're going to use
        self.rows = len(groups) / self.cols
        if len(groups) % self.cols > 0:
            self.rows += 1

        # Call out to our parent constructor
        super(GroupTable, self).__init__(self.rows, self.cols)

        # Populate
        cur_row = 0
        cur_col = 0
        for group in groups:
            self.attach(self._new_button(group), cur_col, cur_col+1, cur_row, cur_row+1, 0, 0)
            cur_col += 1
            if cur_col == self.cols:
                cur_col = 0
                cur_row += 1

    def _new_button(self, group):
        """
        Creates a new button
        """
        button = GroupButton(self, group)
        self.buttons.append(button)
        return button

    def notify_clicked(self, clickedbutton):
        """
        Called by a button when it's clicked on.  This emulates the behavior
        of a RadioButton but allows there to be no button selected at all.
        """
        for button in self.buttons:
            if button != clickedbutton:
                button.set_active(False)
        if self.selector is not None:
            self.selector.filter_group(clickedbutton.group)

    def notify_unclicked(self):
        """
        A button has been un-clicked; we'll notify the selection list.
        """
        if self.selector is not None:
            self.selector.filter_group(None)

class InvNotebook(gtk.Notebook):
    """
    Our main inventory notebook
    """

    def __init__(self, parentwin, items, enchantments, texfiles, app):
        super(InvNotebook, self).__init__()
        self.set_size_request(600, 350)
        self.app = app

        # First page: usual group of items
        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(5, 5, 110, 110)
        itemdetails = InvDetails(parentwin, items, enchantments)
        align.add(itemdetails)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(align)
        self.invtable = InvTable(items, enchantments, itemdetails, texfiles['gui.png'])
        worldvbox = gtk.VBox()
        worldvbox.pack_start(self.invtable, False, True)
        worldvbox.pack_start(gtk.HSeparator(), False, True)
        worldvbox.pack_start(sw, True, True)
        self.append_page(worldvbox, gtk.Label('Inventory'))

        # Second page: overflow items we don't support directly
        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(5, 5, 110, 110)
        itemdetails2 = InvDetails(parentwin, items, enchantments)
        align.add(itemdetails2)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(align)
        self.extrainvtable = ExtraInvTable(items, enchantments, itemdetails2, texfiles['gui.png'])
        worldvbox = gtk.VBox()
        worldvbox.pack_start(self.extrainvtable, False, True)
        worldvbox.pack_start(gtk.HSeparator(), False, True)
        worldvbox.pack_start(sw, True, True)
        self.append_page(worldvbox, gtk.Label('Extra Slots'))

    def populate_from(self, inventory):
        """
        Populates from the given inventory set.
        """
        extra_items = self.invtable.populate_from(inventory)
        self.extrainvtable.populate_from(extra_items)

    def export_inv_nbt(self):
        """
        Exports our inventory data as a fresh NBT file
        """
        return self.invtable.export_nbt() + self.extrainvtable.export_nbt()

    def repair_all(self):
        """
        Repairs all items contained in the book
        """
        self.invtable.repair_all()
        self.extrainvtable.repair_all()

    def fill_all(self):
        """
        Fills all items contained in the book to their maximum capacity
        """
        self.invtable.fill_all()
        self.extrainvtable.fill_all()

    def enchant_all(self):
        """
        Enchants all items with all applicable enchantments
        """
        self.invtable.enchant_all()
        self.extrainvtable.enchant_all()

    def max_ench(self):
        """
        Brings all existing enchantments up to their maximum values
        """
        self.invtable.max_ench()
        self.extrainvtable.max_ench()

    def update_tabs(self):
        """
        Update our tab labels appropriately
        """
        if self.app.multiplayer:
            (path, filename) = os.path.split(self.app.filename)
            title = '%s Inventory' % (filename)
        else:
            if self.app.leveldat['Data'].value['LevelName'] is not None:
                title = '%s Inventory' % (self.app.leveldat['Data'].value['LevelName'].value)
            else:
                title = 'Inventory'
        self.set_tab_label(self.get_nth_page(0), gtk.Label(title))
        if (len(self.extrainvtable.buttons) > 0):
            self.get_nth_page(1).show()
        else:
            self.get_nth_page(1).hide()

class PyInvEdit(gtk.Window):
    """
    Main PyInvedit class
    """

    def __init__(self, yamlfile):
        super(PyInvEdit, self).__init__(gtk.WINDOW_TOPLEVEL)
        global about_name, about_version
        self.set_title('%s %s - Minecraft Inventory Editor' % (about_name, about_version))
        self.set_size_request(900, 800)
        self.connect('delete-event', self.action_quit)
        
        # Load our YAML
        self.load_from_yaml(yamlfile)

        # Figure out what single-player worlds we have available
        avail_worlds = self.get_avail_worlds()

        # The main VBox
        self.mainvbox = gtk.VBox()
        self.add(self.mainvbox)

        # First our menus
        self.mainvbox.pack_start(self.get_menu(), False, False)

        # Now an HBox to hold our components
        mainhbox = gtk.HBox()
        self.mainvbox.add(mainhbox)
        
        # Big ol' label for when we haven't loaded anything yet
        self.loadmessage = gtk.Alignment(.5, .5, 1, 1)
        label = gtk.Label()
        label.set_markup('<b>Open a Minecraft Level...</b>')
        self.loadmessage.add(label)
        self.loadmessage.set_size_request(600, 350)
        mainhbox.pack_start(self.loadmessage, True, True)

        # World Notebook
        align = gtk.Alignment(0, 0, 1, 1)
        align.set_padding(5, 5, 5, 5)
        self.worldbook = InvNotebook(self, self.items, self.enchantments, self.texfiles, self)
        align.add(self.worldbook)
        mainhbox.pack_start(align, False, False)

        # And finally our actual item area (rightmost pane)
        self.itembox = ItemSelector(self.items, self.groups.values())
        mainhbox.add(self.itembox)

        # Make sure everything's shown
        self.show_all()

        # ... but really don't actually show the main world notebook
        self.worldbook.hide()

        # Populate our world submenus (and potentially hide, if we
        # couldn't find any)
        self.populate_world_submenu(self.menu_openfrom, self.load_known, avail_worlds)
        self.populate_world_submenu(self.menu_importfrom, self.import_known, avail_worlds)
        self.populate_world_submenu(self.menu_saveto, self.save_known, avail_worlds)

        # Temporarily disable some menus which should only be active
        # when we've loaded a file
        self.menu_only_loaded = [self.menu_save, self.menu_saveas, self.menu_saveto,
                self.menu_revert, self.menu_repair, self.menu_fill, self.menu_importfrom,
                self.menu_import, self.menu_enchant_all, self.menu_max_ench]
        for menu in self.menu_only_loaded:
            menu.set_sensitive(False)

        # Set up some data
        self.leveldat = None
        self.filename = None
        self.inventory = None
        self.loaded = False

    def about(self, widget, data=None):
        """
        Sets up our About menu
        """
        dialog = dialogs.InvAboutDialog(self)
        dialog.run()
        dialog.destroy()

    def get_menu(self):
        """
        Sets up our menu.  Huzzah for ItemFactory!
        """

        menu_items = (
                ('/_File',                 None,          None,             0, '<Branch>'),
                ('/File/_Open',            '<control>O',  self.load,        0, '<StockItem>', gtk.STOCK_OPEN),
                ('/File/Open From',        None,          None,             0, '<Branch>'),
                ('/File/sep1',             None,          None,             0, '<Separator>'),
                ('/File/_Import',          None,          self.importinv,   0, '<StockItem>', gtk.STOCK_GO_FORWARD),
                ('/File/Import From',      None,          None,             0, '<Branch>'),
                ('/File/sep2',             None,          None,             0, '<Separator>'),
                ('/File/_Save',            '<control>S',  self.save,        0, '<StockItem>', gtk.STOCK_SAVE),
                ('/File/Save _As',         '<control>A',  self.save_as,     0, '<StockItem>', gtk.STOCK_SAVE_AS),
                ('/File/Save To',          None,          None,             0, '<Branch>'),
                ('/File/_Revert to Saved', None,          self.revert,      0, '<StockItem>', gtk.STOCK_REVERT_TO_SAVED),
                ('/File/sep3',             None,          None,             0, '<Separator>'),
                ('/File/_Quit',            '<control>Q',  self.action_quit, 0, '<StockItem>', gtk.STOCK_QUIT),
                ('/_Edit',                 None,          None,             0, '<Branch>'),
                #('/Edit/_Undo',            '<control>Z',  self.menu,        0, '<StockItem>', gtk.STOCK_UNDO),
                #('/Edit/_Redo',            '<control>Y',  self.menu,        0, '<StockItem>', gtk.STOCK_REDO),
                #('/Edit/sep4',             None,          None,             0, '<Separator>'),
                ('/Edit/_Repair All',      '<control>R',  self.repair_all,  0, None),
                ('/Edit/_Fill All',        '<control>F',  self.fill_all,    0, None),
                ('/Edit/_Enchant All',     '<control>E',  self.enchant_all, 0, None),
                ('/Edit/_Maximize Enchantments', '<control>M', self.max_ench, 0, None),
                ('/_Help',                 None,          None,             0, '<Branch>'),
                ('/Help/_About',           None,          self.about,       0, '<StockItem>', gtk.STOCK_ABOUT),
            )
        
        accel_group = gtk.AccelGroup()
        item_factory = gtk.ItemFactory(gtk.MenuBar, '<main>', accel_group)
        item_factory.create_items(menu_items)
        self.add_accel_group(accel_group)
        self.item_factory = item_factory

        # Now construct the menu and modify for the stuff we
        # can't do with our factory
        menu = item_factory.get_widget('<main>')

        # I had been trying to just loop through the menus and
        # pull out the relevant items dynamically (based on label) but
        # the instant you call .get_label() on one of our Factory'd
        # Separator items, they stop rendering properly.  So here's
        # a very stupid way of getting at what I want
        self.menu_openfrom = menu.get_children()[0].get_submenu().get_children()[1]
        self.menu_import = menu.get_children()[0].get_submenu().get_children()[3]
        self.menu_importfrom = menu.get_children()[0].get_submenu().get_children()[4]
        self.menu_save = menu.get_children()[0].get_submenu().get_children()[6]
        self.menu_saveas = menu.get_children()[0].get_submenu().get_children()[7]
        self.menu_saveto = menu.get_children()[0].get_submenu().get_children()[8]
        self.menu_revert = menu.get_children()[0].get_submenu().get_children()[9]
        self.menu_repair = menu.get_children()[1].get_submenu().get_children()[0]
        self.menu_fill = menu.get_children()[1].get_submenu().get_children()[1]
        self.menu_enchant_all = menu.get_children()[1].get_submenu().get_children()[2]
        self.menu_max_ench = menu.get_children()[1].get_submenu().get_children()[3]

        # Tooltips
        self.menu_import.set_tooltip_markup('Imports the inventory from the specified file, while leaving the rest of the savegame intact <i>(world seed, player position, etc)</i>')
        self.menu_importfrom.set_tooltip_markup('Imports the inventory from the specified file, while leaving the rest of the savegame intact <i>(world seed, player position, etc)</i>')
        self.menu_saveto.set_tooltip_markup('Saves our inventory to another file, optionally overwriting the non-inventory data as well <i>(world seed, player position, etc)</i>')
        self.menu_repair.set_tooltip_text('Repairs all damageable items to full health')
        self.menu_fill.set_tooltip_text('Fills all slots to their maximum quantity')
        self.menu_enchant_all.set_tooltip_text('Enchants all items with all available enchantments for that item')
        self.menu_max_ench.set_tooltip_text('Brings all existing item enchantments up to their maximum level')

        # Return
        return menu

    def get_avail_worlds(self):
        """
        Returns a dict of available singleplayer worlds that we could find on
        this machine.  The key will be the name of the dir, the value will
        be the full path
        """
        worlds = {}
        savesdir = mclevelbase.saveFileDir
        if os.path.exists(savesdir):
            for dirent in os.listdir(savesdir):
                dirent_path = os.path.join(savesdir, dirent)
                if os.path.isdir(dirent_path):
                    test_path = os.path.join(dirent_path, 'level.dat')
                    if os.path.exists(test_path):
                        worlds[dirent] = test_path
        return worlds

    def populate_world_submenu(self, menu, func, worlds):
        """
        Given a dict of worlds, populate a submenu
        """
        if len(worlds) > 0:
            worldnames = worlds.keys()
            worldnames.sort()
            sub = menu.get_submenu()
            for name in worldnames:
                item = gtk.MenuItem(name)
                item.connect('activate', func, name, worlds[name])
                sub.append(item)
            menu.show_all()
        else:
            menu.set_visible(False)

    def run(self):
        """
        Main run loop
        """
        gtk.main()

    def confirm_replace(self, action):
        """
        Confirm that it's okay to replace our currently-loaded
        file; used for load, revert, and quit.  The passed-in
        action should be the text to put in the dialog.
        """
        global undo
        if undo.is_changed():
            dialog = dialogs.ConfirmReplaceDialog(self, action)
            response = dialog.run()
            dialog.destroy()
            if response == gtk.RESPONSE_YES:
                return True
            else:
                return False
        else:
            return True

    def action_quit(self, widget, data=None):
        """
        Proces our Quit action
        """
        if self.confirm_replace('quit'):
            gtk.main_quit()
            return False
        return True

    def load_known(self, widget, name, path):
        """
        Load a savefile from our known singleplayer maps
        """
        if self.confirm_replace('load'):
            self.load_from_filename(path)

    def load(self, widget, data=None):
        """
        Load a new savefile
        """
        if self.confirm_replace('load'):
            dialog = dialogs.LoaderDialog(self)
            filename = dialog.load()
            dialog.destroy()
            if filename is not None:
                self.load_from_filename(filename)

    def _load_from_filename(self, path):
        """
        Loads our NBT data from the given path and returns it, or None
        if there was an error.  Will throw a dialog for the user if there
        was an error.  Also sets the var self.last_load_multiplayer as a
        boolean, if what we loaded was a multiplayer server's player.dat
        file, as opposed to the singleplayer level.dat (the inventory
        location is different in those)
        """
        try:
            leveldat = nbt.load(path)

            # Doublecheck
            if leveldat is None:
                dialog = gtk.MessageDialog(self,
                        gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                        gtk.MESSAGE_ERROR,
                        gtk.BUTTONS_OK)
                dialog.set_title('No Data Loaded')
                dialog.set_markup('No data could be loaded from the specified file!')
                dialog.run()
                dialog.destroy()
                return None

            # More double-checking
            correct_tags = False
            try:
                if 'Data' in leveldat:
                    if 'Player' in leveldat['Data'].value:
                        if 'Inventory' in leveldat['Data'].value['Player']:
                            self.last_load_multiplayer = False
                            correct_tags = True
                elif 'Inventory' in leveldat:
                    self.last_load_multiplayer = True
                    correct_tags = True
            except Exception:
                pass

            if not correct_tags:
                dialog = gtk.MessageDialog(self,
                        gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                        gtk.MESSAGE_ERROR,
                        gtk.BUTTONS_OK)
                dialog.set_title('Not a valid Minecraft level.dat')
                dialog.set_markup('The file chosen was a valid NBT file, but did not contain Minecraft inventory data')
                dialog.run()
                dialog.destroy()
                return None

            return leveldat

        except Exception, e:
            dialog = dialogs.ExceptionDialog(self,
                    'Error Loading File',
                    "There was an error loading the file:\n<tt>%s</tt>" % (filename),
                    e)
            dialog.run()
            dialog.destroy()
            return None

    def load_from_filename(self, path, load_inventory=True):
        """
        Loads a level given a filename.  Returns True or False depending
        on if we were successful, though I don't think anything actually
        checks it (or really needs to, given that we throw a dialog in
        here if there were problems).
        """

        # First, do the actual load
        leveldat = self._load_from_filename(path)
        if leveldat is None:
            return False

        # Store our values
        self.filename = path
        self.leveldat = leveldat
        self.multiplayer = self.last_load_multiplayer

        # Now get to work
        if load_inventory:
            if self.multiplayer:
                self.inventory = Inventory(self.leveldat['Inventory'].value)
            else:
                self.inventory = Inventory(self.leveldat['Data'].value['Player'].value['Inventory'].value)
            self.worldbook.populate_from(self.inventory)
        self.loaded = True
        self.loadmessage.hide()

        # Make sure our main notebook is all good to go.
        self.worldbook.update_tabs()
        self.worldbook.show()

        # Activate any menus that need to be activated
        for menu in self.menu_only_loaded:
            menu.set_sensitive(True)
            
        # Update our Undo object
        global undo
        undo.load()

        # And return True, for that warm fuzzy feeling
        return True

    def importinv(self, widget, data=None):
        """
        Import the inventory data from an existing map and overwrite it
        on this savefile (keeping all other data, like seed, player position,
        etc).
        """
        if self.loaded:
            dialog = dialogs.LoaderDialog(self)
            filename = dialog.load()
            dialog.destroy()
            if filename is not None:
                self.import_known(widget, None, filename)

    def import_known(self, widget, name, path):
        """
        Import the inventory data from an existing map and overwrite it
        on this savefile (keeping all other data, like seed, player position,
        etc).
        """
        if self.loaded:
            leveldat = self._load_from_filename(path)
            if leveldat is None:
                return
            if self.last_load_multiplayer:
                self.inventory = Inventory(leveldat['Inventory'].value)
            else:
                self.inventory = Inventory(leveldat['Data'].value['Player'].value['Inventory'].value)
            self.worldbook.populate_from(self.inventory)
            global undo
            undo.change()
            return

    def revert(self, widget, data=None):
        """
        Reverts to the data on disk
        """
        if self.loaded and self.confirm_replace('revert'):
            self.load_from_filename(self.filename)

    def save_as(self, widget, data=None):
        """
        What do do when our "Save As" is called
        """
        if self.loaded:
            dialog = dialogs.SaveAsDialog(self)
            resp = dialog.run()
            filename = dialog.get_filename()
            overwrite_all = dialog.is_overwrite_all()
            dialog.destroy()
            if resp == gtk.RESPONSE_OK:
                self.filename = filename
                if os.path.exists(filename) and not overwrite_all:
                    # Load everything but the inventory
                    self.load_from_filename(path, False)
                self.save()

    def save_known(self, widget, name, path):
        """
        Saves to one of our known singleplayer paths
        """
        if self.loaded:
            dialog = dialogs.OverwriteConfirmDialog(self, name)
            result = dialog.run()
            overwrite_all = dialog.is_overwrite_all()
            dialog.destroy()
            if result == gtk.RESPONSE_YES:
                self.filename = path
                if os.path.exists(path) and not overwrite_all:
                    # Load everything but the inventory
                    self.load_from_filename(path, False)
                self.save()

    def save(self, widget=None, data=None):
        """
        Save our data
        """
        if self.loaded:
            if self.multiplayer:
                self.leveldat['Inventory'].value = self.worldbook.export_inv_nbt()
            else:
                self.leveldat['Data'].value['Player'].value['Inventory'].value = self.worldbook.export_inv_nbt()
            self.leveldat.saveGzipped(self.filename)
            dialog = gtk.MessageDialog(self,
                    gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                    gtk.MESSAGE_INFO,
                    gtk.BUTTONS_OK)
            dialog.set_title('Saved')
            dialog.set_markup("This savefile has been saved to:\n<tt>%s</tt>" % (self.filename))
            dialog.run()
            dialog.destroy()

            # Update our Undo object
            global undo
            undo.save()

    def repair_all(self, widget, data=None):
        """
        Repairs all items
        """
        if self.loaded:
            self.worldbook.repair_all()

    def fill_all(self, widget, data=None):
        """
        Fills all items to maximum capacity
        """
        if self.loaded:
            self.worldbook.fill_all()

    def enchant_all(self, widget, data=None):
        """
        Puts all available enchantments on all items that
        support it.
        """
        if self.loaded:
            self.worldbook.enchant_all()

    def max_ench(self, widget, data=None):
        """
        Brings all existing enchantments on items up to their
        max levels
        """
        if self.loaded:
            self.worldbook.max_ench()

    def load_from_yaml(self, filename):
        """
        Loads all of our relevant objects from the given YAML filename.

        Really we should be clever and hook into PyYAML's functions
        for handling the loading-into-objects directly, but frankly I
        don't want to take the time to do it.  :)
        """

        data = None
        with open('pyinvedit.yaml', 'r') as df:
            data = df.read()

        if data:
            yaml_dict = yaml.load(data)

            # Load texfiles
            self.texfiles = {}
            for yamlobj in yaml_dict['texfiles']:
                texfile = TexFile(yamlobj)
                self.texfiles[texfile.texfile] = texfile

            # Inject our own GUI yaml file
            texfile = TexFile({ 'texfile': 'gui.png',
                    'dimensions': [16, 16] })
            self.texfiles[texfile.texfile] = texfile

            # Now our groups
            self.groups = collections.OrderedDict()
            for yamlobj in yaml_dict['groups']:
                group = Group(yamlobj, self.texfiles)
                self.groups[group.name] = group

            # Now our enchantments
            self.enchantments = Enchantments()
            for yamlobj in yaml_dict['enchantments']:
                self.enchantments.add_enchantment(yamlobj)

            # And finally our items
            self.items = ItemCollection()
            for yamlobj in yaml_dict['items']:
                self.items.add_item(Item(yamlobj, self.texfiles, self.groups, self.enchantments))

            # A standin Item which we'll use when someone wants to type in
            # an arbitrary ID
            yamlobj = {}
            yamlobj['num'] = 0
            yamlobj['name'] = 'Unknown Item'
            yamlobj['texfile'] = 'gui.png'
            yamlobj['coords'] = [1, 2]
            self.items.add_item(Item(yamlobj, self.texfiles, self.groups, self.enchantments, True))

        else:
            raise Exception('No data found from YAML file %s' %
                    (filename))
