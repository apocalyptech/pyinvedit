#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:

###
### Warning!  This is a work-in-progress and might not
### do the right thing in all situations, though it's
### steadily getting closer.  I think it's pretty generally
### usable on Linux, at least.
###
### TODO: cx_Freeze support (or py2exe or whatever) for
### full Windows bundling.
###
### TODO: Figure out how to get _nbt.pyx in bdist, for
### if building it fails during setup time but could
### possibly succeed at some later date with pyximport
###

import numpy
from setuptools import setup
from setuptools.extension import Extension
from pyinveditlib import about_version

# Use Cython if we can, otherwise just the .c file
nbt_ext_modules = []
try:
    from Cython.Distutils import build_ext
    nbt_ext_modules.append('pyinveditlib/pymclevel/_nbt.pyx')
except ImportError:
    print "Cython not found - using previously-Cython'd .c file instead"
    from setuptools.command.build_ext import build_ext
    nbt_ext_modules.append('pyinveditlib/pymclevel/_nbt.c')

#install_requires = [
#        'yaml',
#        'gtk',
#        'cairo'
#    ]

# External data files we include.  The recommended way to
# do this is with package_data, but that ends up burying
# the datafiles deep in difficult-to-find territory.  We
# want to keep these files easily editable by users, so
# we're using data_files instead.
data_files=[('share/pyinvedit/gfx', [ 'gfx/gui.png', 'gfx/items.png',
                      'gfx/logo.png', 'gfx/special.png',
                      'gfx/terrain.png' ]),
    ('share/pyinvedit/data', [ 'data/pyinvedit.yaml' ]),
    ('share/pyinvedit', [ 'COPYING.txt', 'README.txt',
        'LICENSE-pymclevel.txt', 'LICENSE-wraplabel.txt'])]

setup_args = dict(
    name='PyInvEdit',
    version=about_version,
    description='Minecraft Inventory Editor',
    long_description=open('./README.txt', 'r').read(),
    classifiers=[],
    keywords='minecraft',
    author='Christopher J Kucera',
    author_email='pez@apocalyptech.com',
    url='http://apocalyptech.com/minecraft/pyinvedit/',
    license='BSD License',
    packages=['pyinveditlib', 'pyinveditlib.pymclevel'],
    #install_requires=install_requires,
    zip_safe=False,
    entry_points = {
        'gui_scripts': [
            'pyinvedit = pyinveditlib.launcher:main',
        ]
    },
    data_files=data_files,
    ext_modules = [Extension('pyinveditlib.pymclevel._nbt', nbt_ext_modules)],
    cmdclass = { 'build_ext': build_ext },
    include_dirs=numpy.get_include(),
    )

try:
    setup(**setup_args)
except SystemExit:
    del setup_args['ext_modules']
    del setup_args['cmdclass']
    del setup_args['include_dirs']
    setup(**setup_args)
    print
    print "**************************************************************"
    print "NOTICE: We were unable to compile the accelerated version"
    print "of the NBT processing module.  We've just fallen back to"
    print "including the pure-Python version, which is just as functional"
    print "but a bit slower.  If you're running a bdist or the like, note"
    print "that the resulting distfile may not be ideal."
    print "**************************************************************"
    print
