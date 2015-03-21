#!/usr/bin/env python

from setuptools import setup

# Read long description
with open('README.rst') as f:
    long_description = f.read()

setup(
    name='git-slack',
    version='0.1',
    license='BSD',
    url='http://jonls.dk',
    author='Jon Lund Steffensen',
    author_email='jonlst@gmail.com',

    description='Post Git push information from AMQP to Slack',
    long_description=long_description,

    packages=['git_slack'],
    scripts=['scripts/git-slack'],
    install_requires=[
        'PyYAML',
        'pika'
    ]
)
