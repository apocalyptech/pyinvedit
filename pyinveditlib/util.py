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
import sys
import cStringIO

# This file contains various helper functions and classes which didn't seem
# to really fit elsewhere

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

def get_datafile_path(prefix, filename):
    """
    Gets the path to one of our datafiles, given its directory
    prefix.  There's a number of possibilities here, which we could
    simplify by using package_data in our setup.py and pkgutil.get_data().
    However, I explicitly want our data files easily-accessible by
    end users for modification, if so desired, so they don't really fit
    very well into that model.

    Anyway, there are four possibilities, in the order we check them
    here:

    1) We're frozen into an EXE or whatever.  The datafiles should be
       right in the same dir as the executable.

    2) We're running from the source tree.  The datafiles will be
       accessible by hopping one dir up from __file__

    3) We're running from inside an Egg.  The datafiles will be
       accessible by hopping one dir up from __file__, and then
       descending first into share/pyinvedit.

    4) We're installed to the filesystem, outside an Egg.  The relative
       positions of the datafiles will look something like this:
            lib/python2.7/site-packages/pyinveditlib/util.py
            share/pyinvedit/prefix/filename

    Whew.
    """
    if hasattr(sys, 'frozen'):
        # Frozen EXE-or-whatever
        path = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
        return os.path.join(path, prefix, filename)
    else:
        # Try for source directory
        path = os.path.dirname(os.path.dirname(unicode(__file__, sys.getfilesystemencoding())))
        fullpath = os.path.join(path, prefix, filename)
        if os.path.exists(fullpath):
            return fullpath
        else:
            # See if we were in an Egg
            fullpath = os.path.join(path, 'share', 'pyinvedit', prefix, filename)
            if os.path.exists(fullpath):
                return fullpath
            else:
                # Fall back to filesystem non-Egg installation
                fullpath = os.path.join(path, '..', '..', '..', 'share', 'pyinvedit', prefix, filename)
                return fullpath

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
