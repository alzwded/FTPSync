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
from datetime import datetime
from lib.factory import ModuleFactory

FOUR_MEG = 4 * 1024 * 1024

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
                '''rm -f '{}' '''.format(self.fullpath)],
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
        self.offset, _ = self.m.stat(self.path)
        return self.offset

    def _get_bytes(self, offset):
        toread = FOUR_MEG-1 if offset + FOUR_MEG <= self.sz else self.sz % FOUR_MEG
        start = offset
        end = offset + toread
        return '{}-{}'.format(start, end)

    def drain_to(self, sink):
        if(self.sz is None):
            self.sz, _ = self.m.stat(self.path)

        # don't start at 0 in case we're retrying
        offset = sink.offset

        nblocks = self.sz // FOUR_MEG + (1 if ((self.sz % FOUR_MEG) != 0) else 0);
        nblocks -= offset // FOUR_MEG

        while(nblocks > 0):
            print('blocks left {} sz {}'.format(nblocks, self.sz))
            args = ["curl", "--compressed-ssh", "--insecure", '-u', '{}:'.format(self.m.user), '--key', self.m.key, '-r', self._get_bytes(offset)]
            if self.m.passphrase is not None:
                args.append('--pass')
                args.append(self.m.passphrase)
            args.append('{}:{}{}'.format(self.m.host, self.m.port, urllib.parse.quote(self.fullpath)))
            data = subprocess.check_output(args, env=os.environ)
            sink.write(offset, data)
            offset += FOUR_MEG
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

        print("""SFTP module initialized:
  host: {}
  port: {}
  path: {}
  user: {}
  key: {}
  passphrase: {}""".format(self.host, self.port, self.path, self.user, self.key, '********' if self.passphrase is not None else ''))

    def _list(self, path):
        if(path[-1] != '/'):
            raise Exception("the path arg to this method should have ended in /, but got {}".format(path))
        args = ['curl', '--compressed-ssh', '--insecure', '-l', '-u', '{}:'.format(self.user), '--key', self.key]
        if self.passphrase is not None:
            args.append('--pass')
            args.append(self.passphrase)
        args.append("{}:{}{}".format(self.host, self.port, urllib.parse.quote(path)))
        raw = subprocess.check_output(args, env=os.environ)
        return ["{}{}".format(path, s) for s in raw.decode('utf-8').split("\n") if len(s) > 0 and s != '.' and s != '..']

    def _rlist(self, path, cached=None):
        this_depth = self._list(path) if cached is None else cached
        rval = []
        for p in this_depth:
            try:
                rpath = '{}/'.format(p)
                child = self._list(rpath)
                rval += self._rlist(rpath, child)
            except Exception as err:
                print(repr(err))
                rval.append(p)
        return rval

    def tree(self):
        if(self.path[-1] != '/'):
            raise Exception('self.path should have ended in /!')
        skip = len(self.path)
        return [s[skip:] for s in self._rlist(self.path)]

    def stat(self, path):
        if(path[-1] == '/'):
            raise 'did not expect path to end in /'
        sz = int(subprocess.check_output([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''stat -c '%s' '{}{}' '''.format(self.path, path)],
                env=os.environ).decode('utf-8'))
        tm = datetime.fromtimestamp(int(subprocess.check_output([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''stat -c '%Y' '{}{}' '''.format(self.path, path)],
                env=os.environ).decode('utf-8')))
        print('sftp: ' + repr(('{}{}'.format(self.path, path), sz, tm)))
        return sz, tm

    def open(self, path):
        return FileHandle(self, path)

    def _remoteexists(self, fullpath):
        cp = subprocess.run([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host[7:]),
                '-p', str(self.port),
                '''test -e '{}' '''.format(fullpath)],
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
                '''mv '{}' '{}' '''.format(renfro, rento)],
                env=os.environ)

    @classmethod
    def new(cls, config):
        return Module(config)


ModuleFactory.register('sftp', Module)
