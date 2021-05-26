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

__intname__ = 'ofunctions.file_utils'
__author__ = 'Orsiris de Jong'
__copyright__ = 'Copyright (C) 2017-2021 Orsiris de Jong'
__description__ = 'Various file handling of which get_files_recursive is the most advanced'
__licence__ = 'BSD 3 Clause'
__version__ = '0.9.1'
__build__ = '2021052601'

import json
import logging
import os
import re
import shutil
from contextlib import contextmanager
from datetime import datetime
from fnmatch import fnmatch
from itertools import chain
from threading import Lock
from typing import Callable, Iterable, Union

from command_runner import command_runner

logger = logging.getLogger(__name__)
FILE_LOCK = None


@contextmanager
def _file_lock():
    """
    Simple file lock to make no concurrent file operations happen in threaded / mp workflows
    Use as:
    with _file_lock()
        your_file_code
    """
    # pylint: disable=global-statement
    global FILE_LOCK

    if FILE_LOCK is None:
        FILE_LOCK = Lock()
    FILE_LOCK.acquire()
    yield
    if FILE_LOCK is not None:
        FILE_LOCK.release()


def check_path_access(path: str, check: str = 'R') -> bool:
    """
    Check if a path is accessible, if not, decompose path until we know which part isn't writable / readable
    when writable checks fail, we automatically fallback to readable tests
    This is mostly a debug function, we only log successes in debug level

    We don't rely on os.access since it doesn't work well on Windows:
            os.access also returns True with writable files or links
            os.access does report W_OK with windows directories when they arent supposed to

    :param path: path to check (directory or file)
    :param check: [R/W] check for readability / writability
    :return: bool: do we have desired access ?
    """
    if check == 'W':
        perm_type = 'writable'
    else:
        perm_type = 'readable'

    logger.debug('Checking access to path "{0}"'.format(path))

    def _check_path_access(sub_path: str):
        if os.path.exists(sub_path):
            obj = 'file' if os.path.isfile(sub_path) else 'directory'
            if obj == 'file':
                if check == 'W':
                    try:
                        fp = open(sub_path, 'a')
                        fp.close()
                        res = True
                    except (PermissionError, OSError):
                        res = False
                else:
                    try:
                        fp = open(sub_path, 'r')
                        fp.close()
                        res = True
                    except (PermissionError, OSError):
                        res = False
            # Handle directory tests
            else:
                if check == 'W':
                    try:
                        # Let's create a real file in path in order to check effective write permissions
                        test_file = sub_path + '/.somehopefullyunexistenttestfile' + str(datetime.now().timestamp())
                        open(test_file, 'w')
                        remove_file(test_file)
                        res = True
                    except (IOError, OSError):
                        res = False
                else:
                    try:
                        os.listdir(sub_path)
                        res = True
                    except (PermissionError, OSError):
                        res = False

            if res:
                logger.debug('Path "{0}" is a {1} {2}.'.format(sub_path, perm_type, obj))
            else:
                logger.warning('Path "{0}" is a non {1} {2}.'.format(sub_path, perm_type, obj))
            return res

        else:
            logger.warning('Path "{0}" does not exist or has ACLs that prevent access.'.format(sub_path))
        return False

    def _split_path(path):
        split_path = (path, '')
        can_split = True
        failed_once = False
        while can_split is True:
            if _check_path_access(split_path[0]):
                break
            else:
                failed_once = True
            split_path = os.path.split(split_path[0])
            if split_path[1] == '':
                can_split = False
        return failed_once

    result = _split_path(path)
    if result and check == 'W':
        # If not writable, fallback to a readable test
        perm_type = 'readable'
        check = 'R'
        _split_path(path)

    if result:
        logger.warning('Path "{0}" {1} check failed.'.format(path, check))
    return not result


def make_path(path: str):
    with _file_lock():
        # May be false even if dir exists but ACLs deny
        if not os.path.isdir(path):
            os.makedirs(path)


def remove_file(path: str):
    with _file_lock():
        # May be false even if dir exists but ACLs deny
        if os.path.isfile(path):
            os.remove(path)


def remove_dir(path: str):
    with _file_lock():
        # May be false even if dir exists but ACLs deny

        # We need to use shutil.rmtree() instead of os.remove() since the latter implementation
        # produces random "WindowsError: [Error 5] Access is denied" when python process still uses the dir for
        # some unobvious reason
        if os.path.isdir(path):
            shutil.rmtree(path)


def move_file(source: str, dest: str):
    make_path(os.path.dirname(dest))
    with _file_lock():
        # Using copy function because we don't want metadata, permissions, buffer nor anything else
        shutil.move(source, dest, copy_function=shutil.copy)


def glob_path_match(path: str, pattern_list: list) -> bool:
    """
    Checks if path is in a list of glob style wildcard paths
    :param path: path of file / directory
    :param pattern_list: list of wildcard patterns to check for
    :return: Boolean
    """
    return any(fnmatch(path, pattern) for pattern in pattern_list)


def log_perm_error(path: str) -> None:
    """
    Default function that gets executed on get_paths_recursive permission error
    """

    logger.warning('Non handled permission error on "{}"'.format(path))


def get_paths_recursive(root: str, d_exclude_list: list = None, f_exclude_list: list = None,
                        d_include_list: list = None, f_include_list: list = None,
                        exclude_dirs: bool = False, exclude_files: bool = False,
                        ext_exclude_list: list = None, ext_include_list: list = None,
                        min_depth: int = 1, max_depth: int = 0,
                        primary_root: str = None, fn_on_perm_error: Callable = None,
                        ) -> Union[Iterable, str]:
    """
    Walk a path to recursively find files
    Accepts glob style windcards for every list parameter except file extension lists

    Examples:

    for dir in get_paths_recursive('/var', d_exclude_list=['/var/log', '/var/li*'], exclude_files=True, max_depth=4):
        print(dir)

    for file in get_paths_recursive('/var', exclude_dirs=True, depth=2):
        print(file)

    for file in  get_paths_recursive(r'C:\Windows', ext_include_list=['.cmd'], exclude_dirs=True, max_depth=2)
        print(file)

    :param root: (str) path to explore
    :param d_exclude_list: (list) list of root relative directory paths to exclude from path walking
    :param f_exclude_list: (list) list of filenames without paths to exclude from results
    :param d_include_list: (list) list of root relative directory paths to only include from path walking (after exclusion processing)
    :param f_include_list: (list) list of filenames without paths to only include from results (after exclusion processing)
    :param exclude_dirs: (bool) Exclude directories from results
    :param exclude_files: (bool) Exclude files from results
    :param ext_exclude_list: list() list of file extensions to exclude, ex: ['.log', '.bak']
    :param ext_include_list: (list) list of file extensions to include (after exclusion processing) ex: ['.py']
    :param min_depth: (int) minimal depth of results to show, defaults to 1 being the root and it's files
    :param max_depth: (int) depth of recursion, 0 means unlimited, 1 is the root, 2 would be one subdirectory
    :param primary_root: (str) Only used for internal recursive exclusion lookup, don't pass an argument here
    :param fn_on_perm_error: (function) Optional function to pass, which argument will be the file / directory that
           has permission errors so it can be handled
           If not given, permission errors are logged
    :return: chained iterator of files found in path
    """

    # Make sure we don't get paths with antislashes on Windows
    if os.path.isdir(root):
        root = os.path.normpath(root)
    else:
        raise FileNotFoundError('{} is not a directory.'.format(root))

    # Check if we are allowed to read directory, if not, try to fix permissions if fn_on_perm_error is passed
    try:
        os.listdir(root)
    except PermissionError:
        if fn_on_perm_error is not None:
            fn_on_perm_error(root)
        else:
            log_perm_error(root)

    # Make sure we clean d_exclude_list only on first function call
    if primary_root is None:
        if d_exclude_list is not None:
            # Make sure we use a valid os separator for exclusion lists
            d_exclude_list = [os.path.normpath(dir) for dir in d_exclude_list]
        if d_include_list is not None:
            d_include_list = [os.path.normpath(dir) for dir in d_include_list]

        # Let's also make sure that min_depth parameter is used as in gnu find
        min_depth = min_depth - 1

    def _find_files(min_depth):
        if min_depth < 1:
            try:
                if not exclude_dirs:
                    yield root
                if not exclude_files:
                    for file in os.listdir(root):
                        file_ext = os.path.splitext(file)[1]
                        if os.path.isfile(os.path.join(root, file)) and \
                                (f_exclude_list and not glob_path_match(file, f_exclude_list)) and \
                                (ext_exclude_list and file_ext not in ext_exclude_list) and \
                                (not f_include_list or f_include_list and glob_path_match(file, f_include_list)) and \
                                (not ext_include_list or file_ext in ext_include_list):
                            yield os.path.join(root, file)
            except PermissionError:
                pass

    def _find_files_in_dirs(min_depth, max_depth):
        min_depth = min_depth - 1
        if max_depth == 0 or max_depth > 1:
            max_depth = max_depth - 1 if max_depth > 1 else 0
            try:
                for dir in os.listdir(root):
                    d_full_path = os.path.join(root, dir)
                    if os.path.isdir(d_full_path):
                        # p_root is the relative root the function has been called with recursively
                        # Let's check if p_root + d is in d_exclude_list
                        p_root = os.path.join(primary_root, dir) if primary_root is not None else dir
                        if (d_exclude_list and not glob_path_match(p_root, d_exclude_list)) and \
                           (not d_include_list or glob_path_match(p_root, d_include_list)):
                            files_in_d = get_paths_recursive(d_full_path,
                                                             d_exclude_list=d_exclude_list,
                                                             f_exclude_list=f_exclude_list,
                                                             ext_exclude_list=ext_exclude_list,
                                                             ext_include_list=ext_include_list,
                                                             d_include_list=d_include_list,
                                                             f_include_list=f_include_list,
                                                             exclude_dirs=exclude_dirs,
                                                             exclude_files=exclude_files,
                                                             min_depth=min_depth,
                                                             max_depth=max_depth,
                                                             primary_root=p_root,
                                                             fn_on_perm_error=fn_on_perm_error,
                                                             )
                            if files_in_d:
                                for file in files_in_d:
                                    yield file

            except PermissionError:
                pass

    # Chain both file and directory generators
    return chain(_find_files(min_depth), _find_files_in_dirs(min_depth, max_depth))


def get_files_recursive(root: str, d_exclude_list: list = None, f_exclude_list: list = None,
                        ext_exclude_list: list = None, ext_include_list: list = None,
                        depth: int = 0, primary_root: str = None, fn_on_perm_error: Callable = None,
                        include_dirs: bool = False) -> Union[Iterable, str]:
    """
    Wrapper for ofunctions.file_utils < 0.9.0 code
    """

    return get_paths_recursive(root,
                               d_exclude_list=d_exclude_list,
                               f_exclude_list=f_exclude_list,
                               exclude_dirs=not include_dirs,
                               ext_exclude_list=ext_exclude_list,
                               ext_include_list=ext_include_list,
                               min_depth=1, max_depth=depth,
                               primary_root=primary_root,
                               fn_on_perm_error=fn_on_perm_error,
                               )


def replace_in_file(source_file: str, text_to_search: str, replacement_text: str, dest_file: str = None,
                    backup_ext: str = None) -> None:
    """

    :param source_file: source file to replace text in
    :param text_to_search: text to search
    :param replacement_text: text to replace the text to search with
    :param dest_file: optional destination file if inplace replace is not wanted
    :param backup_ext: optional backup extension if no dest_file is given (inplace)
    :return:
    """
    with open(source_file, 'r') as fp:
        data = fp.read()

    if dest_file is not None:
        file = dest_file
    elif backup_ext is not None:
        file = source_file
        backup_file = source_file + backup_ext
        with open(backup_file, 'w') as fp:
            fp.write(data)
    else:
        file = source_file

    data = data.replace(text_to_search, replacement_text)

    with open(file, 'w') as fp:
        fp.write(data)


def get_file_time(path_to_file: str, mac_type: str = 'ctime') -> float:
    """
    Returns file ctime/mtime/atime

    Heaviliy modified version of:
    Source: https://stackoverflow.com/a/39501288/2635443
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.

    Returned epochs are always UTC under Linux
    Returned epochs are TZ under Windows
    """
    if mac_type not in ['ctime', 'mtime', 'atime']:
        raise ValueError('Invalid file MAC time type request')
    try:
        return getattr(os.path, 'get' + mac_type)(path_to_file)
    # Some linuxes may not have os.path.getctime ?
    except AttributeError:
        stat = os.stat(path_to_file)
        try:
            return getattr(stat, 'st_' + mac_type)
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime


def file_creation_date(path_to_file: str) -> float:  # COMPAT <0.7.8
    """
    Wrapper for get_file_time (kept for compatibility reasons)
    """
    return get_file_time(path_to_file, 'ctime')


def file_modification_date(path_to_file: str) -> float:  # COMPAT <0.7.8
    """
    Wrapper for get_file_time (kept for compatibility reasons)
    """
    return get_file_time(path_to_file, 'mtime')


def check_file_timestamp_delta(file: str, mac_type: str = 'ctime', years: int = 0, days: int = 0, hours: int = 0,
                       minutes: int = 0, seconds: int = 0) -> bool:
    """
    mac_type can be ctime, mtime, or atime for comparison purposes

    Simple check if a file is newer/older (ctime) than given time delta from now
    Can also check if file has been modified (mtime) earlier than given time delta from now

    Future timestamps are achieved by specifying positive values, eg days=1
    Past timestamps are achieved by specifying negative values, eg days=-1

    """
    if not os.path.isfile(file):
        raise FileNotFoundError('[%s] not found.' % file)
    delta = seconds + (minutes * 60) + (hours * 3600) + (days * 86400) + (years * 31536000)
    # file creation date is UTC for Linux, TZ for Windows
    if os.name == 'nt':
        now = datetime.now().timestamp()
    else:
        now = datetime.utcnow().timestamp()
    return bool((now + delta - get_file_time(file, mac_type)) > 0)


def is_file_older_than(file: str, years: int = 0, days: int = 0, hours: int = 0,
                       minutes: int = 0, seconds: int = 0) -> bool:  # COMPAT <0.7.8
    """
    Wrapper for check_file_times kept for compatibility
    """
    mac_type = 'ctime'
    return check_file_timestamp_delta(file, mac_type='ctime', years=-years, days=-days,
                                      hours=-hours, minutes=-minutes, seconds=-seconds)


def remove_files_on_timestamp_delta(directory: str, mac_type: str = 'ctime', years: int = 0, days: int = 0,
                                    hours: int = 0, minutes: int = 0, seconds: int = 0) -> None:
    """
    Remove files older than given delta from now
    """

    if not os.path.isdir(directory):
        raise FileNotFoundError('[%s] not found.' % directory)

    for _, _, filenames in os.walk(directory):
        for filename in filenames:
            filename = os.path.join(directory, filename)
            try:
                if check_file_timestamp_delta(filename, mac_type=mac_type, years=years, days=days,
                                              hours=hours, minutes=minutes, seconds=seconds):
                    os.remove(filename)
            except FileNotFoundError:
                pass
            except (IOError, OSError):
                raise OSError('Cannot remove file [%s].' % filename)


def remove_files_older_than(directory: str, years: int = 0, days: int = 0, hours: int = 0,
                            minutes: int = 0, seconds: int = 0) -> None:  # COMPAT <0.7.8
    """
    Wrapper for remove_files_on_timestamp_delta for compatibility
    """
    mac_type = 'ctime'
    remove_files_on_timestamp_delta(directory, mac_type='ctime',
                                    years=-years, days=-days,
                                    hours=-hours, minutes=-minutes, seconds=-seconds)


def remove_bom(file: str) -> None:
    """Remove BOM from existing UTF-8 file"""
    if os.path.isfile(file):
        try:
            with open(file, 'rb') as file_handle_in:
                data = file_handle_in.read(3)
                with open(file + '.tmp', 'wb') as file_handle_out:
                    if data == b'\xef\xbb\xbf':
                        data = file_handle_in.read(32768)
                    while len(data) > 0:
                        file_handle_out.write(data)
                        data = file_handle_in.read(32768)
        except Exception:
            raise OSError
        if os.path.isfile(file + '.tmp'):
            os.replace(file + '.tmp', file)
    else:
        raise FileNotFoundError('[%s] not found.' % file)


def write_json_to_file(file: str, data: Union[dict, list]):
    """
    Creates a manifest to the file containing it's sha256sum and the installation result

    :param file: File to write to
    :param data: Dict to write
    :return:
    """

    with open(file, 'w', encoding='utf-8') as file_handle:
        json.dump(data, file_handle, ensure_ascii=False)


def read_json_from_file(file: str) -> dict:
    """
    Verifies exit code of the file manifest and returns True if installed successfully
    :param file: (str) path to file
    :return:
    """

    if os.path.isfile(file):
        with open(file, 'r', encoding='utf-8') as file_handle:
            file_content = json.load(file_handle)
            return file_content
    else:
        return {}


def grep(file: str, pattern: str) -> list:
    if os.path.isfile(file):
        result = []
        with open(file, 'r') as file_handle:
            for line in file_handle:
                if re.search(pattern, line):
                    result.append(line)
        return result

    raise FileNotFoundError(file)


def hide_windows_file(file: str, hidden: bool = True) -> None:
    if os.name == 'nt':
        if hidden:
            symbol = '+'
        else:
            symbol = '-'
        result, _ = command_runner('attrib %sh "%s"' % (symbol, file))
        if result != 0:
            raise IOError(file)
