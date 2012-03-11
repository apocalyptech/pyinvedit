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
import cairo
import collections
from pyinveditlib import util, minecraft

# This file contains classes that primarily represent the utility data
# that we store in the main YAML file, in a way that's useful to us.

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
        self.filename = util.get_datafile_path('gfx', self.texfile)
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
        if not os.path.exists(self.filename):
            raise Exception('texfile %s not found' % (self.texfile))

        # And while we're at it, load and process it
        mainsurface = None
        try:
            mainsurface = cairo.ImageSurface.create_from_png(self.filename)
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
                self.grid_pixbuf[x][y] = util.get_pixbuf_from_surface(ind_surf)

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
        return minecraft.InventorySlot(num=self.num, damage=self.data, count=self.max_quantity, slot=slot)

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
