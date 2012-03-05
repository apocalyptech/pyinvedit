#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

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

from pyinvedit import pyinveditapp
app = pyinveditapp.PyInvEdit('items.yaml')
app.run()
