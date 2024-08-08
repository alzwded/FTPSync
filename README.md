FTPSync
=======

Python tool to synchronize directory trees across FTP, SFTP and local disk.

## `rsync` exists, why not use that?

`rsync` doesn't do FTP and I have an old local FTP server `:-)`.

Usage
-----

`FTPSync` runs in two stages:

1. generate report
2. batch execute

In order to run, you need a config file. For example, to sync FTP to SFTP:

```ini
[General]
CompareSize = yes     ; default; check file sizes to determine changes
CompareTimestamp = no ; default; this script doesn't set timestamps on the remote, so it's more of a FIXME
ParseFTPLs = yes      ; default; uses ftputil.stat.UnixParser to parse the output of ftp/pure-sftp list to determine sz and tm
ThreadedLS = yes      ; default; gets the directory listing on both remotes using threads
;UseHash = md5        ; defaut off; if set, and supported by the module, it will compute a checksum using the specified algorithm, e.g. md5

[Reference]
protocol = ftp
host = 192.168.0.42
port = 21
user = ftp
password = reallybadpassword
path = /backup

[Mirror]
protocol = sftp
host = sftp.example.com
port = 22
user = me
key = /home/me/.ssh/sftp_ed25519
passphrase = put_this_in_if_applicable_curl_doesnt_talk_to_ssh_agent
path = /backup
```

SFTP only works with key pairs. `ed25519` is probably the best idea in 2022. If you have a passphrase, add it to ssh-agent (for ssh commands, without a timeout) and add the `passphrase` entry in the config (for curl commands). C.f. `/etc/ssh/ssh_config`, `AddKeysToAgent=timeout`. You should `ssh-add` it manually.

SFTP is also a bit janky in that I use `ssh` commands in order to stat files or rename (much faster). So right now, it doesn't work if the remote allows SFTP but dissalows a remote shell. But all is not lost, I've added the 'pure-sftp' module (protocol). Use that if you want pure sftp shennanigans. It is a bit slower, but it seems to work.

The [`bashftp`](https://github.com/alzwded/bashftp) module requires installation on the ~~victim~~ target machine. This is usable on OpenBSD or Alpine which don't have sftp enabled in curl. I *could* rewrite the sftp modules to use sftp instead of curl, but that's a problem for future me. Otherwise, this requires SSH to work between the machines, keys and all.

To mirror a folder from an sftp server (which doesn't allow getting a shell) to your local disk:

```ini
[Reference]
protocol = pure-sftp
host = 192.168.0.42
key = /home/me/.ssh/justsftp_ed25519
path = /backup/photos

[Mirror]
protocol = file
path = /home/me/Pictures
```

You can find more examples [in the tests](./vm/confs).

Let's call the config file `config.conf`.

You can now generate the report:

```sh
FTPSync.py -c config.conf
```

Which writes `merge.xsync` (you can control the file name with `-w command_file_name`). That file looks something like this:

```ini
; File reference
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
; Reference was ftp://192.168.0.42:21/backup
; Mirror was sftp://sftp.example.com:22/backup

[Upload]
a.1 = !

[Extra]
b/c.4 = s
b/c.5 = s

[Merge]
; ref = 200 20:06:22 26-05-2022 mir = 239 14:22:01 27-05-2022
c/modified = s
```

The paths are relative to the `path` config option. Since this is a sync tool, we assume the trees to mostly match.

File modifications are determined purely by file size. There is a `CompareTimestamp=yes/no` option to check timestamps, but right now the files aren't `touch`ed to apply the reference timestamp to the mirror, so you probably don't want to use that.

The intention is that you review it and change the `!sk` characters to suit your needs. You can also arbitrarily add entries under `[Merge]` to force overwriting files you know are different. E.g. I know I changed a byte in `c/changed`, so I'll add a line `c/changed = !` to overwrite or `c/changed = k` to keep both copies. Or you can keep a `commands.xsync` around that always uploads files with `k` if you're taking poor man's snapshots (I don't).

The `[Extra]` section is informative and tells you which files exist on the mirror but not on your reference. This is informative. Remind me to add a flag to not report `[Extra]` in case you're using the mirror as a write only dump and relying on the `k` option to keep extra copies around `:-)`.

The `[Upload]` section only does something if the action is `!`. `k` wouldn't make sense, and this section exists just to be informative that you have new files.

The `[Merge]` section also lists the size and timestamp on the reference and mirror, respectively.

After review, you can execute the batch:

```sh
FTPSync.py -c config.conf -x merge.xsync
```

File uploads are done in 4MB chunks.

If the network drops, it sleeps 2 minutes and tries 2 more times to continue the upload, after which is gives up. This is untested.

Errors should be logged to 'error.log', but you might want to keep an eye on stdout as well. The 'error.log' is only written at the very end, though.

So after you execute your transfer, it's a good idea to generate a report again to see what worked.

# Installing/Development/Testing

FTPSync runs on Linux. Mostly Ubuntu and Alpine, I don't have others `:-)`.

This relies on `curl` compiled `--with-libssh2 --with-openssl`. It also runs find, stat, mv and so on. It is written in python3 using whatever packages are available out of the box. The tests are bash and python scripts. Other than that, no other dependencies that I can think of.

Protocols are handled by [modules](./modules). You can add new ones there (like a better sftp or an scp (for fun) or some other arcane telnet or whatever). The rest of the code just orchestrates diffs and transfers.

For testing, I have [notes](./vm/NOTES.txt) on how to set up an Alpine Linux VM to run the tests. During development, you probably don't want to run the tests using a real FTP or SFTP server; but you can.

When setting up, make sure the test user is `alpine` with password `alpine` and add the `alpine` passphrase to the SSH key. Also, make sure you clone the repo in `/hom/alpine/FTPSync`. If you deviate from these defaults, you need to update all the test [configs](./vm/confs). The intention with that VM is that it's standalone and not connected to anything, so default passwords shouldn't be a problem `:-)`.

I picked Alpine because something usually breaks because I'm so used to Ubuntu/Debian, I can't tell when something is standard or a Debianism. And yeah, I did find issues `:-)`

The tests are run in ~~3~~ many configurations, e.g. `ftp` `->` `sftp` `->` `local` `->` `ftp`. This highlighted a lot of problems. `pure-sftp` is also swapped in for `sftp` to test that as well. And there are 2 more variations for each combination: parse the output of FTP LS being turned off, and getting the file trees from two threads.

I think the 6 or so tests have good enough coverage to prove it works.

FTP is a weird beast, so it's a good idea to run the tests in `local->ftp` and `ftp->local` configurations to check it works with your ftp server software.

The tests themselves are in [vm/tests](./vm/tests); the test "framework" is [vm/utils/testing.sh](./vm/utils/testing.sh) and the test "harness" is [vm/run\_tests.sh](./vm/run_tests.sh). The tests have a basic `SETUP()` where you change the default layout and specify the expected `merge.xsync` and the commands to actually execute; and then there's a `CHECK()` function to check what `FTPSync` did and if it did things correctly.

A 20MB temp file is created to simulate large files.

You can run a single test in all configs using `run_tests.sh tests/onetest`.

The VM is important, since [the default configs](./vm/confs) have some pretty hard coded absolute paths.

3rd party
=========

This project uses `ftputil` by Stefan Schwarzer.

Copyright (C) 2006-2018, Stefan Schwarzer <sschwarzer@sschwarzer.net>
