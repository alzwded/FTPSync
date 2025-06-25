TODO
====

- [ ] bashftp resets to offset 0 on network hiccup, it should reset back to prev block... I think it was this way because of how silly the ftp and sftp modules were, actually
- [ ] deal with empty files better across modules
- [ ] test the (non-pure) sftp on an OpenBSD host; hint: stat probably will error out like it did for the local file: module
- [ ] option to ignore dot files
  + [ ] conversely, option to include dot files; i.e. make it consistent
        across modules
- [ ] perform transfers on 2-N worker threads
