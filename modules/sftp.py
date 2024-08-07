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

import subprocess
import re
import os
import urllib.parse
import re
from datetime import datetime
from lib.factory import ModuleFactory

searchpass = re.compile("""'--pass', '.*', 'sftp://""")

def _anon(s):
    global searchpass
    return re.sub(searchpass, """'--pass', '***REDACTED***', 'sftp://""", s)
    

class FileHandle:
    def __init__(self, module, path):
        self.m = module
        self.path = path
        self.fullpath = '{}{}'.format(self.m.path, path)
        if(self.fullpath[-1] == '/'):
            raise Exception('the path arg should not end in /, but got {}'.format(path))
        self.sz = None
        self.offset = 0

    def _format_C(cls, offset):
        if(offset == 0):
            return ''
        else:
            return '-C {}'.format(offset)

    def write(self, offset, data):
        if(self.offset == 0):
            _ = subprocess.check_output([
                'ssh', '-C',
                '-i', self.m.key,
                '{}@{}'.format(self.m.user, self.m.host[7:]),
                '-p', str(self.m.port),
                '''rm -f {} '''.format(   ''.join([ "\\{}".format(c) for c in self.fullpath])    )],
                env=os.environ)
        args = ["curl", "--compressed-ssh", "--insecure", "--ftp-create-dirs", "-T", "-", "-a", "-u", '{}:'.format(self.m.user), "--key", self.m.key]
        if self.m.passphrase is not None:
            args.append('--pass')
            args.append(self.m.passphrase)
        args.append("{}:{}{}".format(self.m.host, self.m.port, urllib.parse.quote(self.fullpath)))
        _ = subprocess.run(args, check=True, input=data, env=os.environ)
        self.offset += len(data)

    def rewind(self):
        self.offset = 0

    def ff(self):
        self.offset, _, _ = self.m.stat(self.path)
        return self.offset

    def _get_bytes(self, offset):
        toread = self.m.block_size-1 if offset + self.m.block_size <= self.sz else self.sz % self.m.block_size
        start = offset
        end = offset + toread
        return '{}-{}'.format(start, end)

    def drain_to(self, sink):
        if(self.sz is None):
            self.sz, _, _ = self.m.stat(self.path)

        # don't start at 0 in case we're retrying
        offset = sink.offset

        nblocks = self.sz // self.m.block_size + (1 if ((self.sz % self.m.block_size) != 0) else 0);
        nblocks -= offset // self.m.block_size

        while(nblocks > 0):
            print('blocks left {} sz {}'.format(nblocks, self.sz))
            args = ["curl", "--compressed-ssh", "--insecure", '-u', '{}:'.format(self.m.user), '--key', self.m.key, '-r', self._get_bytes(offset)]
            if self.m.passphrase is not None:
                args.append('--pass')
                args.append(self.m.passphrase)
            args.append('{}:{}{}'.format(self.m.host, self.m.port, urllib.parse.quote(self.fullpath)))
            data = subprocess.check_output(args, env=os.environ)
            sink.write(offset, data)
            offset += self.m.block_size
            nblocks -= 1

class Module:
    def __init__(self, config):
        self.host = 'sftp://{}'.format(config['host'])
        if(self.host[-1:] == '/'):
            self.host = self.host[0:-1]
        self.port =  config['port'] if 'port' in config else 22
        self.user =  config['user'] if 'user' in config else os.getlogin()
        self.key = config['key'] if 'key' in config else '~/.ssh/id_rsa'
        self.path =  config['path'] if 'path' in config else '/'
        self.passphrase = config['passphrase'] if 'passphrase' in config else None
        if(self.path[-1] != '/'):
            self.path += '/'
        self.location = '{}:{}{}'.format(self.host, self.port, self.path)
        self.stats = None
        self.block_size = config['BlockSize']

        print("""SFTP module initialized:
  host: {}
  port: {}
  path: {}
  user: {}
  key: {}
  passphrase: {}""".format(self.host, self.port, self.path, self.user, self.key, '********' if self.passphrase is not None else ''))

    def tree(self):
        if(self.path[-1] != '/'):
            raise Exception('self.path should have ended in /!')
        skip = len(self.path)
        # check=False because lost+found will cause -exec to fail,
        # so just grab what we can
        raw = subprocess.run([
            'ssh', '-C',
            '-i', self.key,
            '{}@{}'.format(self.user, self.host[7:]),
            '-p', str(self.port),
            '''find '{}' -type f -print -exec stat -c %s '{{}}' ';' -exec stat -c %Y '{{}}' ';' '''.format(self.path)],
            check=False,
            stdout=subprocess.PIPE).stdout
        lines = [l for l in raw.decode('utf-8').split("\n") if (len(l) > 0)]
        self.stats = {}
        for i in range(len(lines) // 3):
            fname = lines[3*i+0]
            sz = lines[3*i+1]
            tm = lines[3*i+2]
            self.stats[fname] = { 'sz': int(sz), 'tm': int(tm) }
        return [s[skip:] for s in self.stats.keys()]

    def stat(self, path):
        if(path[-1] == '/'):
            raise 'did not expect path to end in /'
        if(self.stats is not None):
            fp = '{}{}'.format(self.path, path)
            if fp not in self.stats:
                raise Exception('file {} does not exist'.format(fp))
            return self.stats[fp]['sz'], datetime.fromtimestamp(self.stats[fp]['tm']), ''
        fullpath = "".join(["\\{}".format(c) for c in '{}{}'.format(self.path, path)])
        sz = int(subprocess.check_output([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''stat -c '%s' {} '''.format(   fullpath   )],
                env=os.environ).decode('utf-8'))
        tm = datetime.fromtimestamp(int(subprocess.check_output([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''stat -c '%Y' {} '''.format(fullpath)],
                env=os.environ).decode('utf-8')))
        print('sftp: ' + repr(('{}{}'.format(self.path, path), sz, tm)))
        return sz, tm, ''

    def open(self, path):
        return FileHandle(self, path)

    def _remoteexists(self, fullpath):
        cp = subprocess.run([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''test -e {} '''.format(  "".join(["\\{}".format(c) for c in fullpath])    )],
                check=False,
                capture_output=False,
                env=os.environ)
        return cp.returncode == 0

    def rename(self, path):
        i = 1
        renfro = '{}{}'.format(self.path, path)
        while(self._remoteexists('{}.{}'.format(renfro, i))):
            i += 1
        rento = '{}.{}'.format(renfro, i)

        print('will rename {} to {}'.format(renfro, rento))
        _ = subprocess.check_output([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''mv {} {} '''.format("".join(["\\{}".format(c) for c in renfro]), "".join(["\\{}".format(c) for c in rento]))],
                env=os.environ)

    @classmethod
    def new(cls, config):
        return Module(config)


ModuleFactory.register('sftp', Module)
