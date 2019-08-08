#!/usr/bin/env python

from setuptools import setup, find_packages

# Change docs/sphinx/conf.py too!

try:
    long_description = open('README.rst', 'rt').read()
except IOError:
    long_description = ''

setup(
    name='USBEncoder',
    version = 0.1,
    description='Read and manage USB quadrature encoder from Measurement Computing',
    long_description=long_description,

    author='Ryan McDowell, John Donnal',
    author_email='donnal@usna.edu',

    download_url='https://github.com/wattsworth/usbquad',
    license='open source (see LICENSE)',
    classifiers=['Programming Language :: Python',
                 'Environment :: Console',
                 ],
    platforms=['Any'],
    scripts=[],
    provides=[],
    install_requires=['joule',
                      'uldaq',
                      'uvloop',
                      'aiohttp',],
    namespace_packages=[],
    packages=find_packages(exclude=["tests.*"]),
    include_package_data=True,

    entry_points={
            'console_scripts': [
                'mccdaq-reader = mccdaq.reader:main',
            ]
        },


    #options={
    #    'build_scripts': {
    #        'executable': '/usr/local/bin/python3.5'
    #    }
    #},
    zip_safe=False,
)
