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

COUNTER=0

T_make_20M_file() {
    cp "$THETEMPFILE" "$1"
}

T_make_3_9M_file() {
    dd if="$THETEMPFILE" of="$1" bs=4096 count=1000
}

T_default_setup() {
    DIR=$1

    echo $DIR > $DIR/canary
    mkdir $DIR/folder1
    echo a > $DIR/folder1/a
    mkdir "$DIR/folder1/My Pictures"
    mkdir "$DIR/folder1/My Pictures/Holiday 1"
    echo photo.jpg > "$DIR/folder1/My Pictures/Holiday 1/photo.jpg"
    mkdir "$DIR/folder1/My Pictures/Holiday 2"
    echo photo.jpg > "$DIR/folder1/My Pictures/Holiday 2/photo.jpg"
    echo photo1.jpg > "$DIR/folder1/My Pictures/Holiday 2/photo.jpg.1"
    mkdir "$DIR/folder1/My Pictures/Holiday 2/Videos"
    T_make_20M_file "$DIR/folder1/My Pictures/Holiday 2/Videos/seagull.mp4"
    T_make_3_9M_file "$DIR/folder1/My Pictures/Holiday 2/Videos/a smile.mp4"
    mkdir "$DIR/folder1/My Documents"
    echo 'Untitled 1.docx' > "$DIR/folder1/My Documents/Untitled 1.docx"
    echo 'Untitled 2.docx' > "$DIR/folder1/My Documents/Untitled 2.docx"
    mkdir "$DIR/folder1/My Documents/Empty"
}

T_small_modification() {
    echo "modified $COUNTER" >> "$1"
    RVAL=$COUNTER
    COUNTER=`expr $COUNTER + 1`
    return $RVAL
}

T_big_modification() {
    echo "modified $COUNTER" >> "$1"
    dd if="$THETEMPFILE" of="$1" oflag=append bs=1024 count=2
    RVAL=$COUNTER
    COUNTER=`expr $COUNTER + 1`
    return $RVAL
}

T_check_modified() {
    grep "${2-modified}" "$1" && return 0 || return 1
}

T_check_unmodified() {
    grep "${2-modified}" "$1" && return 1 || return 0
}

T_check_same() {
    diff "reference/$1" "mirror/$1" > /dev/null 2>&1 && return 0 || return 1
}

T_check_different() {
    diff "reference/$1" "mirror/$1" > /dev/null 2>&1 && return 1 || return 0
}

T_check_missing() {
    test -e "$1" && return 1 || return 0
}

T_compare_configs() {
    "$VMDIR/utils/compare_configs.py" "$1" "$2"
    return $?
}
