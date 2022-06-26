#!/usr/bin/env python3
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
from lib.factory import ModuleFactory
import lib.config

#ftp_mod = modules.ftp.instance()
#sftp_mod = modules.sftp.instance()
#file_mod = modules.file.instance()

ARGS = 'c:h'

def usage():
    global ARGS
    print("""Usage: {} -{}""".format(sys.argv[0], ARGS))
    exit(1)

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
    for opt, arg in optlist:
        if(opt == '-h'):
            usage()
        if(opt == '-c'):
            config = arg

    if config is None:
        print("Expected config file")
        usage()

    reference_config, mirror_config = lib.config.parse_config(config)
    reference = ModuleFactory.new(reference_config)
    mirror = ModuleFactory.new(mirror_config)

    #print(repr(reference.tree()))
    #print(repr(mirror.tree()))

    for f in reference.tree():
        print(repr({'file': f, 'stats': reference.stat(f)}))
    for f in mirror.tree():
        print(repr({'file': f, 'stats': mirror.stat(f)}))

if __name__ == "__main__":
    main()
