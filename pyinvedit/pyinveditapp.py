#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import sys
import math
import yaml
import cStringIO
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

class InventorySlot(object):
    """
    Holds information about a particular inventory slot
    """

    def __init__(self, num=None, damage=None, count=None, slot=None, extratags=None, other=None):
        """
        Initializes a new object.  There are sort of two ways of doing this.
        1) Pass in all of: num, damage, count, slot, and extratags
        2) Pass in: slot and "other", other being an InventorySlot item to copy.  The one thing
           that we won't copy is the slot parameter
        """
        self.slot = slot
        if other is None:
            self.num = num
            self.damage = damage
            self.count = count
            self.extratags = extratags
        else:
            self.num = other.num
            self.damage = other.damage
            self.count = other.count
            self.extratags = extratags

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

class InvDetails(gtk.Table):
    """
    Class to show our inventory item details
    """
    def __init__(self, items):
        super(InvDetails, self).__init__(3, 5)

        self.items = items
        self.itemtitle = gtk.Label()
        align = gtk.Alignment(.5, .5, 1, 1)
        align.add(self.itemtitle)
        self.attach(align, 0, 2, 0, 1, gtk.FILL, gtk.FILL)
        self.button = None
        self.updating = True
        self.var_cache = {}

        self._rowlabel(1, 'Slot Number')
        self.slotdisplay = gtk.Label()
        align = gtk.Alignment(0, .5, 0, 0)
        align.set_padding(3, 3, 5, 0)
        align.add(self.slotdisplay)
        self.attach(align, 1, 2, 1, 2, gtk.FILL, gtk.FILL)

        self._rowlabel(2, 'ID')
        self._rowspinner(2, 'num', 0, 4095)

        self._rowlabel(3, 'Damage/Data')
        self._rowspinner(3, 'damage', 0, 65535)
        self._rowextra(3, 'damage_ext')

        self._rowlabel(4, 'Count')
        self._rowspinner(4, 'count', 1, 255)
        self._rowextra(4, 'count_ext')

    def _rowlabel(self, row, text):
        """
        A label on the given row
        """
        label = gtk.Label()
        label.set_markup('<b>%s:</b>' % (text))
        align = gtk.Alignment(1, .5, 0, 0)
        align.add(label)
        self.attach(align, 0, 1, row, row+1, gtk.FILL, gtk.FILL)

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
        self.attach(align, 2, 3, row, row+1, gtk.FILL, gtk.FILL)

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
        self.slotdisplay.set_text(str(self.button.slot))
        if self.button.inventoryslot is None:
            self._get_var('num').set_value(0)
            self._get_var('damage').set_value(0)
            self._get_var('damage_ext').set_text('')
            self._get_var('count').set_value(1)
            self._get_var('count_ext').set_text('')
            self.itemtitle.set_text('No Item')
            self._get_var('damage').set_sensitive(False)
            self._get_var('count').set_sensitive(False)
        else:
            self._get_var('damage').set_sensitive(True)
            self._get_var('count').set_sensitive(True)
            self._get_var('num').set_value(self.button.inventoryslot.num)
            self._get_var('damage').set_value(self.button.inventoryslot.damage)
            self._get_var('count').set_value(self.button.inventoryslot.count)
            item = self.items.get_item(self.button.inventoryslot.num, self.button.inventoryslot.damage)
            if item:
                self.itemtitle.set_text(item.name)
                self._get_var('count_ext').set_markup('<i>(maximum quanity: %d)</i>' % (item.max_quantity))
                if item.max_damage is None:
                    self._get_var('damage_ext').set_text('')
                else:
                    self._get_var('damage_ext').set_markup('<i>(maximum damage: %d)</i>' % (item.max_damage))
            else:
                self.itemtitle.set_text('Unknown Item')
                self._get_var('damage_ext').set_text('')
                self._get_var('count_ext').set_text('')
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
            print 'Error: no InventorySlot in our button'
            return

        self.button.inventoryslot.num = self._get_var('num').get_value()
        self.button.inventoryslot.damage = self._get_var('damage').get_value()
        self.button.inventoryslot.count = self._get_var('count').get_value()
        self._update_info()
        self.button.update_graphics()

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
            if slotinfo.damage > 0:
                if item is None:
                    # No item data to compare against, assume that it's wrong, I guess
                    self._text_at('%d' % (slotinfo.damage), [1, 0, 0, 1], [0, 0, 0, 1], self.CORNER_NW)
                elif item.max_damage is None:
                    # No max damage defined, so check for the Unique ID to see if we're a known data
                    # type or not.
                    if item.data == slotinfo.damage:
                        # We're good, show nothing
                        pass
                    else:
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
        if self.window is not None:
            self.window.invalidate_rect(gtk.gdk.Rectangle(0, 0, self.size, self.size), True)
            self.window.process_updates(True)

    def get_pixbuf(self):
        """
        Returns our currently-displayed image as a gtk.gdk.Pixbuf
        """
        df = cStringIO.StringIO()
        self.surf.write_to_png(df)
        loader = gtk.gdk.PixbufLoader()
        loader.write(df.getvalue())
        loader.close()
        df.close()
        return loader.get_pixbuf()

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

    def __init__(self, slot, items, detail, empty=None):
        super(InvButton, self).__init__()
        self.set_mode(False)
        # TODO: Get the button size down properly
        self.set_size_request(63, 63)
        self.set_border_width(0)
        self.set_relief(gtk.RELIEF_HALF)
        self.set_active(False)
        self.slot = slot
        self.items = items
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
        #print 'Got a drag from slot %d to %d' % (context.get_source_widget().slot, self.slot)
        other = context.get_source_widget()
        if other.inventoryslot is None:
            self.inventoryslot = None
        else:
            self.inventoryslot = InventorySlot(slot=self.slot, other=other.inventoryslot)

        # Update our graphics and potentially the details area
        if self.get_active():
            self.set_active_state()
        else:
            self.update_graphics()

    def target_drag_motion(self, img, context, x, y, time):
        context.drag_status(context.suggested_action, time)
        return True

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

    def on_clicked(self, button, params=None):
        """
        What to do when we're clicked
        """
        self.set_active_state()

    def set_active_state(self):
        """
        What to do when we become the active button
        """
        self.update_graphics()
        self.detail.update_from_button(self)

    def on_mouse(self, widget, event):
        """
        Process a mouse click (other than our "main" mouse click, which
        will trigger the on_clicked action.
        """
        if event.button == 3:
            self.set_active(True)
            # Right-click, fill stack or repair damage
            if self.inventoryslot is not None:
                item = self.items.get_item(self.inventoryslot.num, self.inventoryslot.damage)
                if item is not None:
                    if item.max_damage is not None:
                        self.inventoryslot.damage = 0
                    elif self.inventoryslot.count < item.max_quantity:
                        self.inventoryslot.count = item.max_quantity
                self.set_active_state()

class InvTable(gtk.Table):
    """
    Table to store inventory info
    """

    def __init__(self, items, detail, icon_head, icon_torso, icon_legs, icon_feet):
        super(InvTable, self).__init__(5, 9)

        self.buttons = {}
        self.group = None
        self.items = items
        self.detail = detail

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
        
        # Make sure that all is well here
        self.update_active_button()

    def _new_button(self, x, y, slot, ypadding=0, empty=None):
        """
        Adds a new button at the specified coordinates, representing the specified
        inventory slot.
        """
        if slot in self.buttons:
            raise Exception("Inventory slot %d already exists" % (slot))
        button = InvButton(slot, self.items, self.detail, empty)
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
        self.update_active_button()

    def update_active_button(self):
        """
        Loops through all our buttons and makes sure that the proper one is
        set as the fully-active button.
        """
        for button in self.buttons.values():
            if button.get_active():
                button.set_active_state()
                break

class PyInvEdit(gtk.Window):
    """
    Main PyInvedit class
    """

    def __init__(self, yamlfile):
        super(PyInvEdit, self).__init__(gtk.WINDOW_TOPLEVEL)
        self.set_title('PyInvEdit - Minecraft Inventory Editor')
        self.set_size_request(800, 600)
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

        # First the world notebook (leftmost pane)
        self.worldbook = gtk.Notebook()
        self.worldbook.set_size_request(600, 350)
        mainhbox.pack_start(self.worldbook, False, False)

        # Now our group icons (middle pane)
        grouptable = gtk.Table()
        mainhbox.pack_start(grouptable, False, False)

        # And finally our actual item area (rightmost pane)
        self.itembox = gtk.VBox()
        mainhbox.add(self.itembox)

        # The first world page
        self.itemdetails = InvDetails(self.items)
        self.invtable = InvTable(self.items, self.itemdetails,
                self.texfiles['items.png'].get_tex(15, 0, True),
                self.texfiles['items.png'].get_tex(15, 1, True),
                self.texfiles['items.png'].get_tex(15, 2, True),
                self.texfiles['items.png'].get_tex(15, 3, True),
                )
        worldvbox = gtk.VBox()
        worldvbox.pack_start(self.invtable, False, True)
        worldvbox.pack_start(gtk.HSeparator(), False, True)
        worldvbox.pack_start(self.itemdetails, False, True)
        self.worldbook.append_page(worldvbox, gtk.Label('Test'))

        # Make sure everything's shown
        self.show_all()

        # Set up some data
        self.leveldat = None
        self.inventory = None

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
            self.items = ItemCollection()
            for yamlobj in yaml_dict['items']:
                self.items.add_item(Item(yamlobj, self.texfiles, self.groups))
        else:
            raise Exception('No data found from YAML file %s' %
                    (filename))
