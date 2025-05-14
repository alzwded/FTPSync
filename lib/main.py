# FTPSync -- ugly sync-over-anything script
# Copyright (C) 2022  Vlad Meșco
#
# This file is part of FTPSync
# 
# FTPSync is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import sys
import os
import getopt
import functools
import time
from lib.factory import ModuleFactory
import lib.config
from lib.ftb import FormatTB
import traceback

#ftp_mod = modules.ftp.instance()
#sftp_mod = modules.sftp.instance()
#file_mod = modules.file.instance()

ARGS = 'c:hVx:w:'
VERSION = '0.9.12'
DEFAULT_TRIES = 10
DEFAULT_SECONDS = 2 * 60

def usage():
    global ARGS
    print("""Usage: {} -{}""".format(sys.argv[0], ARGS))
    exit(1)

def version():
    print("""FTPSync {}""".format(VERSION))
    exit(1)

def upload_file(i, reference, mirror):
    print('Uploading {} from {} to {}'.format(i, reference.location, mirror.location))
    refh = reference.open(i)
    mirh = mirror.open(i)
    tries_left = DEFAULT_TRIES
    while(tries_left > 0):
        tries_left -= 1
        try:
            refh.drain_to(mirh)
            break
        except Exception as err:
            print(err)
            traceback.print_exc()
            if tries_left > 0:
                print('trying {} more times after {}s'.format(tries_left, DEFAULT_SECONDS))
                mirh.rewind()
                time.sleep(DEFAULT_SECONDS)
            else:
                print('giving up')
                raise err

def execute_commands(commands, reference, mirror):
    log = []
    if "Upload" in commands:
        print('Processing [Upload]')
        s = commands['Upload']
        for i in s:
            action = s[i]
            if(action == '!'):
                try:
                    upload_file(i, reference, mirror)
                except Exception as err:
                    _, _, exc_traceback = sys.exc_info()
                    log.append('ERROR: failed to UPLOAD {} last reason {} traceback {}'.format(i, err, FormatTB(exc_traceback)))
    if "Merge" in commands:
        print('Processing [Merge]')
        s = commands['Merge']
        for i in s:
            action = s[i]
            if(action == '!'):
                try:
                    upload_file(i, reference, mirror)
                except Exception as err:
                    _, _, exc_traceback = sys.exc_info()
                    log.append('ERROR: failed to MERGE=! {} last reason {} traceback {}'.format(i, err, FormatTB(exc_traceback)))
            elif(action == 'k'):
                try:
                    print('renaming {} on {}'.format(i, mirror.location))
                    ntries = DEFAULT_TRIES
                    while(ntries > 0):
                        ntries -= 1
                        try: 
                            mirror.rename(i)
                            break
                        except Exception as err:
                            _, _, exc_traceback = sys.exc_info()
                            print(err)
                            print(FormatTB(exc_traceback))
                            if(ntries > 0):
                                print('trying {} more times after {}s'.format(ntries, DEFAULT_SECONDS))
                                time.sleep(DEFAULT_SECONDS)
                            else:
                                raise err
                except Exception as err:
                    _, _, exc_traceback = sys.exc_info()
                    log.append('ERROR: failed to RENAME {} last reason {} traceback {}'.format(i, err, FormatTB(exc_traceback)))
                    continue
                ok = False
                try:
                    mirror.stat(i)
                except:
                    ok = True
                if(ok):
                    try:
                        upload_file(i, reference, mirror)
                    except Exception as err:
                        _, _, exc_traceback = sys.exc_info()
                        log.append('ERROR: failed to upload during MERGE=k for {} last reason {} traceback {}'.format(i, err, FormatTB(exc_traceback)))
                else:
                    log.append('ERROR: failed to KEEP {} file is still there after rename, cowardly refusing to overwrite file!'.format(i))
    with open('error.log', 'w') as f:
        f.writelines(['{}\n'.format(line) for line in log])
    return len(log)

def process_commands1(execute, reference, mirror):
    commands = lib.config.parse_commands(execute)
    def countBangs(s, k):
        if(s[k] == '!'):
            return 1
        else:
            return 0
    def countKeeps(s, k):
        if(s[k] == 'k'):
            return 1
        else:
            return 0
    def countSkips(s, k):
        if(s[k] == 's'):
            return 1
        else:
            return 0
    for section_name in commands:
        section = commands[section_name]
        if(section_name == 'Upload'):
            print('{} new files to upload'.format(
                    functools.reduce(lambda a, x: a + countBangs(section, x), section.keys(), 0)
                    ))
            print('{} new files skipped'.format(
                    functools.reduce(lambda a, x: a + countSkips(section, x), section.keys(), 0)
                    ))
        elif(section_name == 'Extra'):
            print('{} extra files on mirror'.format(len(section)))
        elif(section_name == 'Merge'):
            print('{} files will be overwritten'.format(
                    functools.reduce(lambda a, x: a + countBangs(section, x), section.keys(), 0)
                    ))
            print('{} files will be renamed on mirror and new copies uploaded'.format(
                    functools.reduce(lambda a, x: a + countKeeps(section, x), section.keys(), 0)
                    ))
            print('{} files not merged'.format(
                    functools.reduce(lambda a, x: a + countSkips(section, x), section.keys(), 0)
                    ))
    print('Executing...')
    nerrors = execute_commands(commands, reference, mirror)
    print('Done')
    if(nerrors > 0):
        print('Review {}'.format('error.log'))
    else:
        print('No errors reported')

def main():
    global ARGS
    optlist, args = (None, None)
    try:
        optlist, args = getopt.getopt(sys.argv[1:], ARGS)
    except:
        usage()

    if(len(args) > 0):
        print("Unexpected arguments");
        usage()

    config = None
    execute = None
    out_commands = 'merge.xsync'
    use_timestamps = False
    for opt, arg in optlist:
        if(opt == '-h'):
            usage()
        if(opt == '-c'):
            config = arg
        if(opt == '-x'):
            execute = arg
        if(opt == '-V'):
            version()
        if(opt == '-w'):
            out_commands = arg

    if config is None:
        print("Expected config file")
        usage()

    general, reference_config, mirror_config = lib.config.parse_config(config)
    # disable UseHash if execute is on to avoid pointlessly computing hashes
    # TODO might as well disable other stuff like timestamps, only size is needed
    if(execute is not None and 'UseHash' in general):
        del general['UseHash']
        del reference_config['UseHash']
        del mirror_config['UseHash']

    # instantiate modules
    reference = ModuleFactory.new(reference_config)
    mirror = ModuleFactory.new(mirror_config)

    if(execute is None):
        lib.config.generate_commands(out_commands, reference, mirror, general)
        print('Done')
        print("""Review {} then run \n    {} -c {} -x {}\nto process batch""".format(
                out_commands,
                sys.argv[0],
                config,
                out_commands))
    else:
        process_commands1(execute, reference, mirror)
        print('You may want to delete {} and rerun\n    {} -c {}\nagain to check state.'.format(
                execute,
                sys.argv[0],
                config,
                ))
