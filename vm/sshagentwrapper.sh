#!/bin/bash

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

"$@"
exit $?
