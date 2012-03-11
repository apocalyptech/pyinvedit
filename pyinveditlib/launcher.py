#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:

import sys

# Load GTK
try:
    import gtk
    import gobject
    import cairo
    import pango
    import pangocairo
except Exception, e:
    # TODO: Should pop up a warning dialog if we can load
    # the base GTK module but not, for whatever reason,
    # Cairo or Pango
    print 'Python GTK Modules not found: %s' % (str(e))
    print 'Hit enter to exit...'
    sys.stdin.readline()
    sys.exit(1)

def main(argv=None):
    from pyinveditlib import pyinveditapp
    app = pyinveditapp.PyInvEdit()
    app.run()

