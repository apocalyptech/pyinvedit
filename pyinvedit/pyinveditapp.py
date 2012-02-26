#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import sys
import yaml
import collections
from pymclevel import nbt

# Load GTK
try:
    import gtk
    import gobject
    import cairo
    import pango
    import pangocairo
except Exception, e:
    print 'Python GTK Modules not found: %s' % (str(e))
    print 'Hit enter to exit...'
    sys.stdin.readline()
    sys.exit(1)

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
        for x in range(0, self.x):
            self.grid_large.append([])
            self.grid_small.append([])
            for y in range(0, self.y):
                self.grid_large[x].append(None)
                self.grid_small[x].append(None)

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

class Item(object):
    """
    Class to hold information about an inventory item.
    """
    def __init__(self, yamlobj, texfiles, groups):
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
        self.texfile.check_bounds(self.x, self.y)

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

    def get_image(self, large=False):
        """
        Returns the base cairo ImageSurface for this item
        """
        return self.texfile.get_tex(self.x, self.y, large)

class InventorySlot(object):
    """
    Holds information about a particular inventory slot
    """

    def __init__(self, num=None, damage=None, count=None, slot=None, extratags=None):
        self.num = num
        self.damage = damage
        self.count = count
        self.slot = slot
        self.extratags = extratags

    def try_ids(self):
        """
        Returns a list of IDs to check against our item registry
        """
        return ['%d~%d' % (self.num, self.damage), self.num]

    def __cmp__(self, other):
        """
        Comparator object for sorting
        """
        return cmp(self.num, other.num)

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
        num = item.value['id'].value
        damage = item.value['Damage'].value
        count = item.value['Count'].value
        slot = item.value['Slot'].value
        extratags = {}
        for tagname, value in item.value.iteritems():
            if tagname not in ['id', 'Damage', 'Count', 'Slot']:
                extratags[tagname] = value
        self.inventory[slot] = InventorySlot(num, damage, count, slot, extratags)

    def get_items(self):
        """
        Gets a list of all items in this inventory set
        """
        return self.inventory.values()

class InvImage(gtk.DrawingArea):
    """
    Class to show an image inside one of our inventory slot buttons.
    This is actually a DrawingArea which uses Cairo to do all the lower-level
    rendering stuff.
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
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.size, self.size)
        self.set_size_request(self.size, self.size)
        self.button = button
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
            self.cr = self.window.cairo_create()
            self.pangoctx = self.get_parent().get_pango_context()
            self.pangolayout = pango.Layout(self.pangoctx)
            self.pangolayout.set_font_description(pango.FontDescription('sans bold 9'))
            self.pangolayout.set_width(self.size)
            self.cairoctx = pangocairo.CairoContext(self.cr)
        self.draw()

    def draw(self):
        """
        The meat of the rendering
        """
        slotinfo = self.button.inventoryslot

        if slotinfo is None:
            # Nothing in this inventory slot
            if self.empty is None:
                self.cr.set_source_rgba(0, 0, 0, 0)
                self.cr.rectangle(0, 0, self.size, self.size)
                self.cr.fill()
            else:
                self._surface_center(self.empty)
        else:
            # Get information about the item, if we can
            imgsurf = None
            item = None
            for uniqueid in slotinfo.try_ids():
                if uniqueid in self.button.items:
                    item = self.button.items[uniqueid]
                    imgsurf = item.get_image(True)
                    break

            # Now get the "base" image
            if imgsurf is None:
                # TODO: Something more graceful
                self.cr.set_source_rgba(1, 0, 0, 1)
                self.cr.rectangle(0, 0, self.size, self.size)
                self.cr.fill()
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
            if slotinfo.damage > 0:
                if item is None or item.max_damage is None or slotinfo.damage > item.max_damage:
                    self._text_at('%d' % (slotinfo.damage), [1, 0, 0, 1], [0, 0, 0, 1], self.CORNER_NW)
                else:
                    percent = 1 - (slotinfo.damage / float(item.max_damage))

                    # The base (black) bar
                    self.cr.set_source_rgba(0, 0, 0, 1)
                    self.cr.rectangle(self.DAMAGE_X, self.DAMAGE_Y, self.DAMAGE_W, self.DAMAGE_H)
                    self.cr.fill()

                    # The actual damage notifier
                    self.cr.set_source_rgba(1-percent, percent, 0, 1)
                    self.cr.rectangle(self.DAMAGE_X, self.DAMAGE_Y, self.DAMAGE_W*percent, self.DAMAGE_H)
                    self.cr.fill()

    def _surface_center(self, surface):
        """
        Draws a cairo surface to the center of the image.
        """
        offset = (self.size - surface.get_width()) / 2
        self.cr.set_source_surface(surface, offset, offset)
        self.cr.move_to(0, 0)
        self.cr.rectangle(offset, offset, surface.get_width(), surface.get_width())
        self.cr.fill()

    def _text_at(self, text, textcolor, outlinecolor, corner):
        """
        Draws some text to our surface at the given location, using the given colors
        for the text and the outline.
        """
        self.pangolayout.set_markup(text)
        (width, height) = map(lambda x: x/pango.SCALE, self.pangolayout.get_size())
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
        self.cairoctx.layout_path(self.pangolayout)
        self.cr.set_source_rgba(*outlinecolor)
        self.cr.set_line_width(2)
        self.cr.stroke()
        self.cr.move_to(x, y)
        self.cr.set_source_rgba(*textcolor)
        self.cairoctx.show_layout(self.pangolayout)

    def update(self):
        """
        Re-queue an update for ourselves
        """
        self.window.invalidate_rect(gtk.gdk.Rectangle(0, 0, self.size, self.size), True)
        self.window.process_updates(True)

class LoaderDialog(gtk.FileChooserDialog):
    """
    A class to load a new minecraft save.
    """
    def __init__(self, parent):
        super(LoaderDialog, self).__init__('Open New Savegame', parent,
                gtk.FILE_CHOOSER_ACTION_OPEN,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.set_default_response(gtk.RESPONSE_OK)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        self.set_current_folder(os.path.join(os.path.expanduser('~'), '.minecraft', 'saves'))
        filter = gtk.FileFilter()
        filter.set_name("Minecraft Savefiles")
        filter.add_pattern("level.dat")
        self.add_filter(filter)

    def load(self):
        resp = self.run()
        if resp == gtk.RESPONSE_OK:
            filename = self.get_filename()
            if os.path.exists(filename):
                return nbt.load(filename)
            else:
                print 'zomg error'
        return None

class InvButton(gtk.RadioButton):
    """
    Class for an individual button on our inventory screen
    """

    def __init__(self, slot, items, empty=None):
        super(InvButton, self).__init__()
        self.set_mode(False)
        # TODO: Get the button size down properly
        self.set_size_request(63, 63)
        self.set_border_width(0)
        self.set_relief(gtk.RELIEF_HALF)
        self.set_active(False)
        self.slot = slot
        self.items = items
        self.inventoryslot = None
        self.image = InvImage(self, empty)
        self.add(self.image)

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

class InvTable(gtk.Table):
    """
    Table to store inventory info
    """

    def __init__(self, items, icon_head, icon_torso, icon_legs, icon_feet):
        super(InvTable, self).__init__(5, 9)

        self.buttons = {}
        self.group = None
        self.items = items

        # Armor slots
        self._new_button(0, 0, 103, 7, empty=icon_head)
        self._new_button(1, 0, 102, 7, empty=icon_torso)
        self._new_button(2, 0, 101, 7, empty=icon_legs)
        self._new_button(3, 0, 100, 7, empty=icon_feet)

        # Ordinary inventory slots
        for i in range(9):
            self._new_button(i, 1, 9+i)
            self._new_button(i, 2, 18+i)
            self._new_button(i, 3, 27+i)
            self._new_button(i, 4, i, 7)

    def _new_button(self, x, y, slot, ypadding=0, empty=None):
        """
        Adds a new button at the specified coordinates, representing the specified
        inventory slot.
        """
        if slot in self.buttons:
            raise Exception("Inventory slot %d already exists" % (slot))
        button = InvButton(slot, self.items, empty)
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

    def populate_from(self, inventory):
        """
        Populates all of our buttons from the given inventory object.
        """
        self.clear_buttons()
        for item in inventory.get_items():
            if item.slot in self.buttons:
                self.buttons[item.slot].update_slot(item)

class PyInvEdit(gtk.Window):
    """
    Main PyInvedit class
    """

    def __init__(self, yamlfile):
        super(PyInvEdit, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.set_title('PyInvEdit - Minecraft Inventory Editor')
        self.set_size_request(800, 400)
        self.connect("destroy", self.action_quit)
        
        # Load our YAML
        self.load_from_yaml(yamlfile)

        # The main VBox
        self.mainvbox = gtk.VBox()
        self.add(self.mainvbox)

        # First our menus
        self.mainvbox.pack_start(self.get_menu(), False, False)

        # Now an HBox to hold our components
        mainhbox = gtk.HBox()
        self.mainvbox.add(mainhbox)

        # First the world notebook
        self.worldbook = gtk.Notebook()
        self.worldbook.set_size_request(500, 350)
        mainhbox.pack_start(self.worldbook, False, False)

        # Now our group icons
        grouptable = gtk.Table()
        mainhbox.pack_start(grouptable, False, False)

        # And finally our actual item area
        self.itembox = gtk.VBox()
        mainhbox.add(self.itembox)

        # The first world page
        self.invtable = InvTable(self.items,
                self.texfiles['items.png'].get_tex(15, 0, True),
                self.texfiles['items.png'].get_tex(15, 1, True),
                self.texfiles['items.png'].get_tex(15, 2, True),
                self.texfiles['items.png'].get_tex(15, 3, True),
                )
        self.worldbook.append_page(self.invtable, gtk.Label('Test'))

        # Testing stuff
        #button = gtk.Button()
        #mybox.pack_start(button, False, False)
        #self.image = TestImage()
        #button.add(self.image)
        #button.connect('clicked', self.clickbutton)

        # Make sure everything's shown
        self.show_all()

        # Set up some data
        self.leveldat = None
        self.inventory = None

    #def clickbutton(self, button):
    #    self.image.update()

    def menu(self, widget, data):
        print 'hoo'

    def get_menu(self):
        """
        Sets up our menu.  Huzzah for ItemFactory!
        """

        menu_items = (
                ('/_File',        None,           None,             0, '<Branch>'),
                ('/File/_New',    '<control>N',   self.menu,        0, '<StockItem>', gtk.STOCK_NEW),
                ('/File/_Open',   '<control>O',   self.load,        0, '<StockItem>', gtk.STOCK_OPEN),
                ('/File/_Save',   '<control>S',   self.menu,        0, '<StockItem>', gtk.STOCK_SAVE),
                ('/File/Save _As', '<control>A',  self.menu,        0, '<StockItem>', gtk.STOCK_SAVE_AS),
                ('/File/sep1',    None,           None,             0, '<Separator>'),
                ('/File/_Quit',   '<control>Q',   self.action_quit, 0, '<StockItem>', gtk.STOCK_QUIT),
                ('/_Edit',        None,           None,             0, '<Branch>'),
                ('/Edit/_Undo',   '<control>Z',   self.menu,        0, '<StockItem>', gtk.STOCK_UNDO),
                ('/Edit/_Redo',   '<control>Y',   self.menu,        0, '<StockItem>', gtk.STOCK_REDO),
                ('/_Help',        None,           None,             0, '<Branch>'),
                ('/Help/_About',  None,           self.menu,        0, '<StockItem>', gtk.STOCK_ABOUT),
            )
        
        accel_group = gtk.AccelGroup()
        item_factory = gtk.ItemFactory(gtk.MenuBar, '<main>', accel_group)
        item_factory.create_items(menu_items)
        self.add_accel_group(accel_group)
        self.item_factory = item_factory
        return item_factory.get_widget('<main>')

    def run(self):
        gtk.main()

    def action_quit(self, widget, data=None):
        gtk.main_quit()

    def load(self, widget, data=None):
        """
        Load a new savefile
        """
        dialog = LoaderDialog(self)
        self.leveldat = dialog.load()
        dialog.destroy()
        self.inventory = Inventory(self.leveldat['Data'].value['Player'].value['Inventory'].value)
        self.invtable.populate_from(self.inventory)

    def load_from_yaml(self, filename):
        """
        Loads all of our relevant objects from the given YAML filename.
        Returns a tuple containing the following:
           * A texfiles dict
           * A groups dict
           * An items dict

        Really we should be clever and hook into PyYAML's functions
        for handling the loading-into-objects directly, but frankly I
        don't want to take the time to do it.  :)
        """

        data = None
        with open('items.yaml', 'r') as df:
            data = df.read()

        if data:
            yaml_dict = yaml.load(data)

            # Load texfiles
            self.texfiles = {}
            for yamlobj in yaml_dict['texfiles']:
                texfile = TexFile(yamlobj)
                self.texfiles[texfile.texfile] = texfile

            # Now our groups
            self.groups = collections.OrderedDict()
            for yamlobj in yaml_dict['groups']:
                group = Group(yamlobj, self.texfiles)
                self.groups[group.name] = group

            # And finally our items
            self.items = collections.OrderedDict()
            for yamlobj in yaml_dict['items']:
                item = Item(yamlobj, self.texfiles, self.groups)
                self.items[item.unique_id] = item
        else:
            raise Exception('No data found from YAML file %s' %
                    (filename))
