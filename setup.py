#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:

###
### Warning!  This is a work-in-progress and isn't really
### suitable for all (or even many) situations.  It works
### well enough when installing to an Egg on Linux, but
### fails in various ways for most other installation
### targets.
###
### TODO: cx_Freeze support (or py2exe or whatever) for
### full Windows bundling.
###

import numpy
from setuptools import setup
from setuptools.extension import Extension
from Cython.Distutils import build_ext as cython_build_ext

version = '1.0.0b1'

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

setup(name='PyInvEdit',
        version=version,
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
        ext_modules = [Extension('_nbt', ['pyinveditlib/pymclevel/_nbt.pyx'])],
        cmdclass = { 'build_ext': cython_build_ext },
        include_dirs=numpy.get_include()
    )

