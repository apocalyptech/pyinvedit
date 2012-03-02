'''
Created on Jul 22, 2011
Modified Mar 2, 2012 to exclude all but the minecraftDir and saveFileDir content

@author: Rio
'''

import os

# we need to decode file paths from environment variables or else we get an error
# if they are formatted or joined to a unicode string
import sys

if sys.platform == "win32":
    #not sure why win32com is needed if the %APPDATA% var is available

    try:
        import win32com.client
        objShell = win32com.client.Dispatch("WScript.Shell")
        appDataDir = objShell.SpecialFolders("AppData")
    except Exception, e:
        print "Error while getting AppData folder using WScript.Shell.SpecialFolders: {0!r}".format(e)
        try:
            from win32com.shell import shell, shellcon
            appDataDir = shell.SHGetPathFromIDListEx(
                shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_APPDATA)
            )
        except Exception, e:
            print "Error while getting AppData folder using SHGetSpecialFolderLocation: {0!r}".format(e)

            appDataDir = os.environ['APPDATA'].decode(sys.getfilesystemencoding())

    minecraftDir = os.path.join(appDataDir, u".minecraft")

elif sys.platform == "darwin":
    appDataDir = os.path.expanduser(u"~/Library/Application Support")

    minecraftDir = os.path.join(appDataDir, u"minecraft")
    minecraftDir.decode(sys.getfilesystemencoding())
else:
    appDataDir = os.path.expanduser(u"~")
    minecraftDir = os.path.expanduser(u"~/.minecraft")


saveFileDir = os.path.join(minecraftDir, u"saves")
