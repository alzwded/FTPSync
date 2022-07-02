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
from lib.ftb import FormatTB
import sys
from threading import Thread

def _invalid_config():
    print("""Example config file:
    [General]
    CompareSize = yes
    CompareTimestamp = no
    ParseFTPLs = yes
    ThreadedLS = no

    [Reference]
    protocol=ftp
    root=/folder1
    host=server.lan
    port=21
    user=johndoe
    password=badpassword

    [Mirror]
    protocol=sftp
    root=/home/user/mirrors/folder1
    host=mars.lan
    port=22
    user=johndoe
    key=~/.ssh/id_rsa
""")
    exit(1)

def parse_config(configpath):
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(configpath)
    if(not config.has_section("Reference") or not config.has_section("Mirror")):
        _invalid_config()

    reference = config['Reference']
    mirror = config['Mirror']

    general = config['General'] if config.has_section('General') else {}
    if 'CompareSize' not in general:
        general['CompareSize'] = 'yes'
    if 'CompareTimestamp' not in general:
        general['CompareTimestamp'] = 'no'
    if 'ParseFTPLs' not in general:
        general['ParseFTPLs'] = 'yes'
    if 'ThreadedLS' not in general:
        general['ThreadedLS'] = 'yes'

    for k in general:
        reference[k] = general[k]
        mirror[k] = general[k]

    return (general, reference, mirror)

SKIP = 's'
OVERWRITE = '!'
RENAME_KEEP = 'k'

def tree_thread(c, files):
    files[:] = c.tree()

def generate_commands(configpath, reference, mirror, general):
    ref_files = []
    mir_files = []
    if general['ThreadedLS'] == 'yes':
        print('!!!! Running tree() on threads !!!!')
        reft = Thread(target=tree_thread, args=(reference, ref_files))
        mirt = Thread(target=tree_thread, args=(mirror, mir_files))
        reft.start()
        mirt.start()
        reft.join()
        mirt.join()
    else:
        print('!!!! Running tree() sequentially !!!!')
        ref_files = reference.tree()
        mir_files = mirror.tree()
    print(repr(ref_files))
    print(repr(mir_files))
    ref_set = set(ref_files)
    mir_set = set(mir_files)

    upload_set = ref_set - mir_set
    extra_set = mir_set - ref_set
    interset = ref_set & mir_set

    differences = {}

    for i in interset:
        ref_sz, ref_tm, mir_sz, mir_tm = None, None, None, None
        if general['CompareTimestamp'] == 'yes' or general['CompareSize'] == 'yes':
            try:
                ref_sz, ref_tm = reference.stat(i)
                ref_tm = ref_tm.strftime('%x %X')
            except Exception as err:
                _, _, exc_traceback = sys.exc_info()
                print(err)
                print(FormatTB(exc_traceback))
                ref_sz = 0
                ref_tm = 'missing'
            try:
                mir_sz, mir_tm = mirror.stat(i)
                mir_tm = mir_tm.strftime('%x %X')
            except Exception as err:
                _, _, exc_traceback = sys.exc_info()
                print(err)
                print(FormatTB(exc_traceback))
                mir_sz = 0
                mir_tm = 'missing'
        else:
            ref_sz = 0
            ref_tm = 'missing'
            mir_sz = 0
            mir_tm = 'missing'

        print(repr((i, ref_sz, ref_tm, mir_sz, mir_tm)))

        if((general['CompareSize'] and ref_sz != mir_sz)
            or (general['CompareTimestamp'] == 'yes' and ref_tm != mir_tm)):
            differences[i] = {
                'ref_sz': ref_sz,
                'ref_tm': ref_tm,
                'mir_sz': mir_sz,
                'mir_tm': mir_tm,
                'action': SKIP
            }

    with open(configpath, "w") as f:
        f.write("""; File reference
; ==============
;
; The Upload section lists files to be uploaded. They default to YES.
; The Extra section informs you about extra files on the mirror.
; The Merge section lists files which are different in terms of size or
; (optionally) timestamp.
;
; Within each section, you'll see 'file = x', where x may be:
; - s           skip this file
; - !           copy/overwrite this file
; - k           rename the file on the mirror appending a .1 (or .N),
;               then proceed to copy the file from the reference
;
; Reference was {}
; Mirror was {}

""".format(
                reference.location,
                mirror.location))
        f.write("[Upload]\n")
        for i in upload_set:
            f.write("{} = {}\n".format(i, OVERWRITE))
        f.write("\n")

        f.write("[Extra]\n")
        for i in extra_set:
            f.write("{} = {}\n".format(i, SKIP))
        f.write("\n")

        f.write("[Merge]\n")
        for k in differences:
            v = differences[k]
            f.write("; ref = {} {} ;; mir = {} {}\n".format(v['ref_sz'], v['ref_tm'], v['mir_sz'], v['mir_tm']))
            f.write("{} = {}\n".format(k, SKIP))

def parse_commands(commandspath):
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(commandspath)
    return config
        
