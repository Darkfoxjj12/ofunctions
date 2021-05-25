#! /usr/bin/env python
#  -*- coding: utf-8 -*-
#
# This file is part of command_runner module

"""
Versioning semantics:
    Major version: backward compatibility breaking changes
    Minor version: New functionality
    Patch version: Backwards compatible bug fixes

"""

__intname__ = 'tests.ofunctions.file_utils'
__author__ = 'Orsiris de Jong'
__copyright__ = 'Copyright (C) 2020-2021 Orsiris de Jong'
__licence__ = 'BSD 3 Clause'
__build__ = '2021051201'

import sys
from time import sleep

from ofunctions.file_utils import *
from ofunctions.random import random_string


def test_check_path_access():
    # logging.basicConfig(level=logging.DEBUG)
    # Hopefully does not exist
    result = check_path_access(r'/somedirthathopefullydoesnotexistinthisuniverse2424', check='W')
    assert result is False, 'check_path_access failed'
    if os.name == 'nt':
        bin_dir = r'C:\Windows\system32'
        tmp_dir = os.path.expandvars('%temp%')
    else:
        bin_dir = '/usr/bin'
        tmp_dir = '/tmp'
    # should be readable
    result = check_path_access(bin_dir, check='R')
    assert result is True, 'Access to bin dir {} should be readable'.format(bin_dir)
    # should be writable
    check_path_access(tmp_dir, check='W')
    assert result is True, 'Access to current temp "{}" should be writable'.format(tmp_dir)


def test_glob_path_match():
    """
    Check that "*est*" matches current "tests" dir
    """
    match = glob_path_match(os.path.dirname(__file__), ['*est*'])
    assert match is True, 'glob_path_match test failed'


def print_perm_error(file):
    """
    This function solely exists for test_get_files_recursive
    """
    print('Perm error on: %s' % file)


def test_get_files_recursive():
    files = get_files_recursive(os.path.dirname(__file__), fn_on_perm_error=print_perm_error)

    assert isinstance(files, chain)
    for file in files:
        print(file)

    files = get_files_recursive(os.path.dirname(__file__))
    assert 'test_bisection.py' in [os.path.basename(file) for file in files], 'get_files_recursive test failed'

    # Include directories in output
    files = get_files_recursive(os.path.dirname(__file__), include_dirs=True)
    assert 'test_json_sanitize.py' in [os.path.basename(file) for file in files], 'get_files_recursive with dirs test failed'

    # Try d_exclude_list on ..\tests
    files = get_files_recursive(os.path.join(os.path.dirname(__file__), os.pardir),
                                d_exclude_list=['tests'], include_dirs=True)
    assert 'tests' + os.sep + 'file_utils.py' not in [os.path.basename(file) for file in
                                 files], 'get_files_recursive with d_exclude_list failed'

    # Try f_exclude_list
    files = get_files_recursive(os.path.dirname(__file__), f_exclude_list=['test_file_utils.py'])
    assert 'test_file_utils.py' not in [os.path.basename(file) for file in
                                   files], 'get_files_recursive with f_exclude_list failed'

    # Try ext_exclude_list
    files = get_files_recursive(os.path.dirname(__file__), ext_exclude_list=['.py'])
    for file in files:
        if file.endswith('.py'):
            assert False, 'get_files_recursive failed with ext_exclude_list'

    # Try f_include_list
    files = get_paths_recursive(os.path.dirname(__file__), f_include_list=['test*utils.py'])
    result_list = [os.path.basename(file) for file in files]
    assert 'test_file_utils.py' in result_list, 'get_paths_recursive with f_include_list failed'
    assert len(result_list) == 1, 'get_paths_recursive with f_include_list failed'

    # Try ext_include_list
    files = get_files_recursive(os.path.dirname(__file__), ext_include_list=['.py'])
    for file in files:
        if not file.endswith('.py'):
            assert False, 'get_files_recursive failed with ext_include_list'


def test_get_file_time():
    for mac_type in ['ctime', 'mtime', 'atime']:
        mac_timestamp = get_file_time(__file__, mac_type)
        print(mac_type, mac_timestamp)
        dt = datetime.fromtimestamp(mac_timestamp)
        assert isinstance(dt, datetime), 'Timestamp could not be converted to datetime object'
        assert 2021 <= dt.year < 2300, 'Code will prabably not run in 200 years, ehh'


def test_check_file_timestamp_delta():
    """
    Windows file creation dates are VERY wrong when requested by python
    The following code will keep earlier file creation dates, even if file is removed
    Hence we'll add some random string to the filename to make sure the tests will not fail
    """
    filename = "test" + random_string(8) + ".file"
    remove_file(filename)
    with open(filename, 'w') as file_handle:
        file_handle.write('test')
    result = check_file_timestamp_delta(filename, years=0, days=0, hours=0, minutes=0, seconds=-2)
    assert result is False, 'Just created file should not be older than 2 seconds'
    sleep(3)
    result = check_file_timestamp_delta(filename, years=0, days=0, hours=0, minutes=0, seconds=-2)
    assert result is True, 'Just created file should now be older than 2 seconds'
    remove_file(filename)

    result = check_file_timestamp_delta(sys.argv[0], years=-200, days=0, hours=0, minutes=0, seconds=0)
    assert result is False, 'Ahh see... A file older than 200 years ? Is my code still running in the year 2221 ?'


if __name__ == '__main__':
    print('Example code for %s, %s' % (__intname__, __build__))
    test_check_path_access()
    test_glob_path_match()
    test_get_files_recursive()
    test_get_file_time()
    test_check_file_timestamp_delta()
