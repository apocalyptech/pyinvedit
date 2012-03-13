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

from pymclevel import nbt

# This file primarily contains classes which represent the actual
# on-disk data for a given savefile, without our abstractions on
# top of it.

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
            self.num = nbtobj['id'].value
            self.lvl = nbtobj['lvl'].value
            self.extratags = {}
            for tagname in nbtobj:
                if tagname not in ['id', 'lvl']:
                    self.extratags[tagname] = nbtobj[tagname]

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
            self.num = nbtobj['id'].value
            self.damage = nbtobj['Damage'].value
            self.count = nbtobj['Count'].value
            self.slot = nbtobj['Slot'].value
            self.enchantments = []
            self.extratagtags = {}
            if 'tag' in nbtobj:
                if 'ench' in nbtobj['tag']:
                    for enchtag in nbtobj['tag']['ench']:
                        self.enchantments.append(EnchantmentSlot(nbtobj=enchtag))
                for tagname in nbtobj['tag']:
                    if tagname not in ['ench']:
                        extratagtags[tagname] = nbtobj['tag'][tagname]
            self.extratags = {}
            for tagname in nbtobj:
                if tagname not in ['id', 'Damage', 'Count', 'Slot', 'tag']:
                    self.extratags[tagname] = nbtobj[tagname]

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
        slot = item['Slot'].value
        self.inventory[slot] = InventorySlot(nbtobj=item)

    def get_items(self):
        """
        Gets a list of all items in this inventory set
        """
        return self.inventory.values()
