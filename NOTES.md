ftpsync
=======

cURL in its CLI and lib form can do FTP and SFTP (and SCP).

It's binary by default.

```sh
# list
curl -u user:passwd ftp://server/dir/
curl -u user:passwd --list-only ftp://server/dir/
# download
curl -u user:pass ftp://server/dir/file -o local/file
curl -u user:pass -r 128-256 ftp://server/dir/file -o local/file
# upload
curl -u user:pass -T local/file --ftp-pasv --ftp-create-dirs ftp://server/dir/file
curl -u user:pass -T local/file -C offset --ftp-pasv ftp://server/dir/file
# get SIZE and Last Modified
curl -I -u user:pass --ftp-pasv ftp://server/.......
# execute any odd command
curl -v -I -u user:pass --ftp-pasv -Q 'CWD /folder1' -Q 'SIZE file.txt' --ftp-create-dirs ftp://server/
# prefix with '-' to execute AFTER CWD and LS and transfer
# prefix with '+' to execute after initial PWD
# e.g. DELE,  RNFR+RNTO, MDTM (modified time), SIZE, 
# for sftp, they are rm, rmdir, rename; no good way to get fstat() over sftp o_O; maybe for size I can do a quick ssh du -b path; and for rename/delete
# and curl might prove problematic for PKI auth (--pubkey and --key? It says curl should pick up id_rsa by itself, but pfff)
```

So I guess that covers:
- list
- stat (size & modified time)
- put
- get
- partial get (-r)
- continue upload (-C)
- rename
- delete

For a sync,
- get listing on both sides
- upload/download new files
- for files on both ends, request SIZE and MDTM and show report; based on user input, overwrite on one end or another or reconcile differences in some other way (e.g. via renames)
- transfers >N MB between two FTP sites should grab N MB chunks at a time using -r/-C
- filesystem driver, remote ftp driver, sftp driver (this has different commands for delete, rename, stat)
- let's write a giant bash script?



Apparently resume doesn't seem to properly work anywhere. I might just change the interface to sound like "append-only" or something like that.
