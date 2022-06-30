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

. utils/testing.sh

VMDIR=$(dirname "$(readlink -f "$0")")
APPDIR=$(dirname "$VMDIR")
export PATH="$APPDIR:$PATH"
export VMDIR

RAN=0
FAILED=0
PASSED=0

declare -a FAILED_TESTS


THETEMPFILE=`mktemp`
trap "rm -f '$THETEMPFILE'" EXIT
echo THETEMPFILE is "$THETEMPFILE"
dd if=/dev/urandom of="$THETEMPFILE" bs=4096 count=5120
echo Done generating THETEMPFILE
export THETEMPFILE

run_single_test() {
    echo '===================================================='
    echo $t
    echo '===================================================='
    for conf in confs/* ; do
        echo $conf
        echo '----------------------------------------------------'
        rm -rf scratch/
        mkdir -p scratch/reference
        mkdir -p scratch/mirror
        T_default_setup scratch/reference
        T_default_setup scratch/mirror
        rm -f scratch/mirror/canary
        bash utils/run_test.sh $t $conf
        STATUS=$?
        case $STATUS in
        0)
            RAN=`expr $RAN + 1`
            PASSED=`expr $PASSED + 1`
            echo OK
            ;;
        1)
            FAILED_TESTS[$FAILED]="$t $conf"
            RAN=`expr $RAN + 1`
            FAILED=`expr $FAILED + 1`
            echo $t $conf FAILED
            exit 1
            ;;
        2)
            ;;
        esac
        echo '----------------------------------------------------'
    done
    echo '===================================================='
    echo ''
}

setup_ssh_agent() {
    TMPFILE=`mktemp`
    ssh-agent > $TMPFILE
    cat $TMPFILE
    . $TMPFILE
    rm $TMPFILE
    ssh-add ~/.ssh/id_ed25519
    trap "rm -f '$THETEMPFILE' ; kill -QUIT $SSH_AGENT_PID" EXIT
}

setup_ssh_agent

if [[ $# > 0 ]] ; then
    echo running subset "$@"
    for t in "$@" ; do
        run_single_test $t
    done
else
    echo running all tests
    for t in tests/*.sh ; do
        run_single_test $t
    done
fi

echo $RAN tests ran
echo $PASSED tests OK
echo $FAILED tests FAILED
if [[ $FAILED > 0 ]] ; then
    echo 'These test-config combos failed:'
    for (( i=0 ; $i < $FAILED ; i=`expr $i + 1` )) ; do
        echo '    '${FAILED_TESTS[$i]}
    done
fi
