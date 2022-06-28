#!/bin/bash
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

SETUP() {
    cat - > expected.xsync  <<EOT
[Upload]
My Pictures/Holiday 2/photo.jpg = !

[Extra]
My Pictures/Holiday 1/photo.jpg = s

[Merge]
EOT
    cat - > execute.xsync <<EOT
[Upload]
My Pictures/Holiday 2/photo.jpg = !

[Extra]

[Merge]
EOT
    rm 'mirror/folder1/My Pictures/Holiday 2/photo.jpg'
    rm 'reference/folder1/My Pictures/Holiday 1/photo.jpg'
}

CHECK() {
    set -x
    T_check_same "folder1/a" || return 1
    T_check_missing "reference/folder1/My Pictures/Holiday 1/photo.jpg" || return 1
    T_check_same "folder1/My Pictures/Holiday 2/photo.jpg" || return 1
    T_check_same "folder1/My Pictures/Holiday 2/photo.jpg.1" || return 1
    T_check_same "folder1/My Pictures/Holiday 2/Videos/seagull.mp4" || return 1
    T_check_same "folder1/My Pictures/Holiday 2/Videos/a smile.mp4" || return 1
    T_check_same "folder1/My Documents/Untitled 1.docx" || return 1
    T_check_same "folder1/My Documents/Untitled 2.docx" || return 1
    return 0
}
