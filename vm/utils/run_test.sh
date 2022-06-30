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

if [[ -z $1 || ! -f $1 || -z $2 || ! -f $2 ]] ; then
    echo "couldn't find the test ($1) or the conf ($2)"
    exit 2
fi

TNAME=$1
CONFNAME=$2
T=`readlink -f $TNAME`
TEST_DIR=`dirname "$T"`
CONF=`readlink -f $CONFNAME`

source $1
source utils/testing.sh

echo CWD to `readlink -f scratch`
pushd scratch || exit 2
echo OK

echo SETUP
SETUP || exit 1
echo OK

if [[ -n ${MYCONFIG+x} ]] ; then
    TMPF=`mktemp`
    test -f "$MYCONFIG" || exit 2
    cat "$MYCONFIG" > "$TMPF"
    cat "$CONF" | grep -v '\[General\]' >> "$TMPF"
    CONF="$TMPF"
    trap "cat '$TMPF' ; rm -f '$TMPF'" EXIT
fi


echo Generating command file
FTPSync.py -c "$CONF" || exit 1
echo OK

echo Checking command file
T_compare_configs "$(readlink -f merge.xsync)" expected.xsync || exit 1
echo OK

echo Executing command file
FTPSync.py -x execute.xsync -c "$CONF" || exit 1
echo OK

echo Checking mirror state
CHECK || exit 1
echo OK

if [[ -f mirror/canary ]] ; then
    echo 'canary should not be present in mirror!'
    exit 1
fi

echo ALL GOOD
exit 0
