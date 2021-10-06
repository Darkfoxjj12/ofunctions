#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of ofunctions package

"""
ofunctions is a general library for basic repetitive tasks that should be no brainers :)

Versioning semantics:
    Major version: backward compatibility breaking changes
    Minor version: New functionality
    Patch version: Backwards compatible bug fixes

"""

__intname__ = "ofunctions"
__author__ = "Orsiris de Jong"
__copyright__ = "Copyright (C) 2014-2021 Orsiris de Jong"
__description__ = "Toolset for files/logging/network/checksumming/process handling"
__licence__ = "BSD 3 Clause"
__version__ = "2.2.1"
__build__ = "2021100602"


# Make sure we declare this file as namespace holder
try:
    __import__("pkg_resources").declare_namespace(__name__)
except ImportError:
    from pkgutil import extend_path

    __path__ = extend_path(__path__, __name__)
