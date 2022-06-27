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
import configparser
import sys

def diff(a, b):
    ca = configparser.ConfigParser()
    ca.read(a)
    cb = configparser.ConfigParser()
    cb.read(b)

    for s in ['Upload', 'Merge', 'Extra']:
        if(len(set(ca[s].keys()) ^ set(cb[s].keys()))):
            raise Exception("Missing or extra keys: {}".format(repr(set(ca[s].keys()) ^ set(cb[s].keys()))))
        for k in set.union(set(ca[s].keys()) , set(cb[s].keys())):
            if ca[s][k] != cb[s][k]:
                raise Exception("{}/{}: {} != {}".format(s, k, ca[s][k], cb[s][k]))

if __name__ == "__main__":
    diff(sys.argv[1], sys.argv[2])
