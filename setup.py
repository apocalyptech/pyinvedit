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

from setuptools import setup
from setuptools.extension import Extension
from Cython.Distutils import build_ext

version = '1.0.0b1'

#install_requires = [
#        'yaml',
#        'gtk',
#        'cairo'
#    ]

nbt_ext_modules = []
nbt_build_ext = {}

import numpy
try:
    from Cython.Distutils import build_ext
    nbt_ext_modules.append('pyinveditlib/pymclevel/_nbt.pyx')
    nbt_build_ext['build_ext'] = build_ext
except ImportError:
    print 'error'
    pass

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
        data_files=[('gfx', [ 'gfx/gui.png', 'gfx/items.png',
                              'gfx/logo.png', 'gfx/special.png',
                              'gfx/terrain.png' ]),
            ('data', [ 'data/pyinvedit.yaml' ])],
        ext_modules = [Extension('_nbt', nbt_ext_modules)],
        cmdclass = nbt_build_ext,
        include_dirs=numpy.get_include()
    )

