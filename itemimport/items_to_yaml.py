#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:

#
# Converts an items.txt (from INVedit) into a YAML format
#
# Does some special processing on a few magic numbers, alas.
#
# Really we should use PyYAML to do the writing, but I didn't feel
# like taking the time to figure out how to get the output
# formatted the way I wanted
#

import re

class Group(object):
    """
    A group that items can live in
    """

    class IconMapping(object):
        """
        I didn't see a sane way to convert these from the given format.
        """
        def __init__(self, texfile, x, y):
            self.texfile = texfile
            self.x = x
            self.y = y

        def toyaml(self):
            lines = []
            lines.append('    texfile: %s' % (self.texfile))
            lines.append('    coords: [%d, %d]' % (self.x, self.y))
            return lines

    mappings = {
            'Natural': IconMapping('terrain.png', 3, 0),
            'Stone': IconMapping('terrain.png', 1, 0),
            'Wood': IconMapping('terrain.png', 4, 0),
            'Mushroom': IconMapping('terrain.png', 13, 4),
            'Nether': IconMapping('terrain.png', 7, 6),
            'TheEnd': IconMapping('terrain.png', 15, 10),
            'Ores': IconMapping('terrain.png', 2, 3),
            'Plants1': IconMapping('terrain.png', 6, 4),
            'Plants2': IconMapping('terrain.png', 15, 0),
            'Farming': IconMapping('items.png', 9, 1),
            'Dye': IconMapping('items.png', 14, 4),
            'Wool': IconMapping('terrain.png', 0, 4),
            'Shovels': IconMapping('items.png', 2, 5),
            'Pickaxes': IconMapping('items.png', 2, 6),
            'Axes': IconMapping('items.png', 2, 7),
            'Hoes': IconMapping('items.png', 2, 8),
            'Swords': IconMapping('items.png', 2, 4),
            'Tools': IconMapping('items.png', 5, 1),
            'Potions': IconMapping('items.png', 0, 14),
            'Logic': IconMapping('items.png', 8, 3),
            'Food': IconMapping('items.png', 9, 2),
            'Items': IconMapping('items.png', 6, 0),
            'SpawnEggs': IconMapping('items.png', 0, 10),
            'Music': IconMapping('items.png', 1, 15),
            'Head': IconMapping('items.png', 15, 0),
            'Chest': IconMapping('items.png', 15, 1),
            'Legs': IconMapping('items.png', 15, 2),
            'Feet': IconMapping('items.png', 15, 3),
            'Buckets': IconMapping('items.png', 10, 4),
            'Special': IconMapping('terrain.png', 11, 1),
            'SplashPotions': IconMapping('items.png', 0, 13),
            'Transport': IconMapping('items.png', 7, 8),
            'Drops': IconMapping('items.png', 14, 1),
        }

    def __init__(self, name):
        self.name = name
        if name in self.mappings:
            self.mapping = self.mappings[name]
        else:
            print 'Unknown category: %s' % (name)
            self.mapping = None

    def toyaml(self):
        lines = []
        lines.append('  - name: %s' % (self.name))
        if self.mapping is not None:
            lines.extend(self.mapping.toyaml())
        lines.append('')
        lines.append('')
        return "\n".join(lines)

class Item(object):
    """
    An item we're capable of having in our inventory.
    """

    def __init__(self, id, name, texfile, cx, cy, damage=None, max_damage=None, max_quantity=None):
        self.id = id
        self.name = name
        self.texfile = texfile
        self.cx = cx
        self.cy = cy
        self.damage = damage
        self.max_damage = max_damage
        self.max_quantity = max_quantity
        self.group = None

    def __cmp__(self, other):
        first = cmp(self.id, other.id)
        if first == 0:
            return cmp(self.damage, other.damage)
        return first

    def toyaml(self):
        # Output
        lines = []
        lines.append('  - id: %d' % (self.id))
        lines.append('    name: %s' % (self.name))
        lines.append('    texfile: %s' % (self.texfile))
        lines.append('    coords: [%d, %d]' % (self.cx, self.cy))
        if self.damage is not None:
            lines.append('    damage: %d' % (self.damage))
        if self.max_damage is not None:
            lines.append('    max_damage: %d' % (self.max_damage))
        if self.max_quantity is not None:
            lines.append('    max_quantity: %d' % (self.max_quantity))
        if self.group is not None:
            lines.append('    group: %s' % (self.group.name))
        lines.append('')
        lines.append('')
        return "\n".join(lines)

if __name__ == '__main__':
    itemre = re.compile('^\s*(\d+)\s+(\S+)\s+(\S+)\s+(\d+),(\d+)\s*(\S*)\s*$')
    timere = re.compile('^(.+) (\d+:\d+)$')
    groupre = re.compile('^~\s+(\S+)\s+(\d+)\s+(\S+)\s*$')
    dictre = re.compile('^(\d+)\~0$')
    items = {}
    groups = []
    with open('items.txt', 'r') as df:

        for line in df.readlines():
            match = itemre.search(line)
            if match:
                id = int(match.group(1))
                name = match.group(2)
                texfile = match.group(3)
                cx = int(match.group(4))
                cy = int(match.group(5))
                mult_col = match.group(6)
                damage = None
                max_damage = None
                max_quantity = None

                # Skip some "special" items which aren't really items at all
                if id > 12340:
                    continue

                # Process the last column
                if mult_col is not None and mult_col != '':
                    prefix = mult_col[0].lower()
                    if prefix == 'x':
                        max_quantity = int(mult_col[1:])
                    elif prefix == '(':
                        # Currently the Compass and Clock use "(x1)" for some reason
                        max_quantity = int(mult_col[2:-1])
                    elif prefix == '+':
                        max_damage = int(mult_col[1:])
                    else:
                        damage = int(mult_col)
                        if damage == 0:
                            damage = None

                # Get rid of the underscores
                name = name.replace('_', ' ')

                # ... and apostrophes
                name = name.replace('\'', '')

                # Various potion special processing
                if id == 373:
                    if name.startswith('Splash '):
                        name = name[7:]
                    if name.lower().find('potion') == -1 and name.lower() != 'water bottle':
                        name = 'Potion of %s' % (name)
                    itemmatch = timere.search(name)
                    if itemmatch:
                        name = '%s (%s)' % (itemmatch.group(1), itemmatch.group(2))
                    if damage is not None and (damage & 0x4000 == 0x4000):
                        name = 'Splash %s' % (name)

                # Store the item
                if damage is not None and damage != 0:
                    dictid = '%d~%d' % (id, damage)
                else:
                    dictid = str(id)
                items[dictid] = Item(id, name, texfile, cx, cy, damage, max_damage, max_quantity)

            # Grouping
            match = groupre.search(line)
            if match:
                name = match.group(1)
                icon = int(match.group(2))
                groupitems = match.group(3)
                if name.startswith('Empty'):
                    continue
                group = Group(name)
                groups.append(group)
                for dictid in groupitems.split(','):
                    dictmatch = dictre.search(dictid)
                    if dictmatch:
                        dictid = dictmatch.group(1)
                    if dictid in items:
                        if items[dictid].group is not None:
                            print 'Duplicate group for %s: %s vs. %s' % (items[dictid].name, items[dictid].group.name, group.name)
                        items[dictid].group = group
                    else:
                        print 'Unknown dictid in group %s: %s' % (group.name, dictid)

    with open('items.yaml', 'w') as odf:
        odf.write("---\n\n")
        odf.write("groups:\n\n")
        for group in groups:
            odf.write(group.toyaml())
        odf.write("items:\n\n")
        for item in sorted(items.values()):
            odf.write(item.toyaml())
        odf.write("...\n")
