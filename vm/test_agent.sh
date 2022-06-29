#!/bin/bash

if [[ $# > 0 ]] ; then
    ssh localhost 'echo from child process'
    ssh localhost 'echo from child process'
    python3 <<EOT
import os
import subprocess

subprocess.run(['ssh', 'localhost', 'echo from python'], check=True, env=os.environ)
EOT
    exit $?
fi


setup_ssh_agent() {
    TMPFILE=`mktemp`
    ssh-agent > $TMPFILE
    cat $TMPFILE
    . $TMPFILE
    rm $TMPFILE
    ssh-add ~/.ssh/id_ed25519
}

setup_ssh_agent
trap "rm -f /tmp/notexistanthopefully ; kill -QUIT $SSH_AGENT_PID" EXIT

ssh localhost 'echo done'
ssh localhost 'echo done'
ssh localhost 'echo done'
$0 asd
