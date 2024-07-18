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

class FileHandle:
    def __init__(self, module, path):
        self.m = module
        self.path = path
        self.fullpath = '{}{}'.format(self.m.path, path)
        if(self.fullpath[-1] == '/'):
            raise Exception('the path arg should not end in /, but got {}'.format(path))
        self.sz = None
        self.offset = 0

    def write(self, offset, data):
        args = ['ssh', '-C', 
            '-i', self.m.key,
            '-p', str(self.m.port),
            '{}@{}'.format(self.m.user, self.m.host),
            """bashftp put {} {} '{}'""".format(offset, offset + self.m.block_size, self.fullpath)]
            #'bashftp', 'put', self.offset, len(data), "\"'{}'\"".format(self.fullpath)]
        _ = subprocess.run(args, check=True, input=data, env=os.environ)
        self.offset += self.m.block_size

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
            args = ['ssh', '-C', 
                '-i', self.m.key,
                '-p', str(self.m.port),
                '{}@{}'.format(self.m.user, self.m.host),
                """bashftp get {} {} '{}'""".format(offset, offset + self.m.block_size, self.fullpath)]
                #'bashftp', 'get', self.offset, len(data), "\"'{}'\"".format(self.fullpath)]
            data = subprocess.check_output(args, env=os.environ)
            sink.write(offset, data)
            offset += self.m.block_size
            nblocks -= 1

class Module:
    def __init__(self, config):
        self.host = config['host']
        if(self.host[-1:] == '/'):
            self.host = self.host[0:-1]
        self.port =  config['port'] if 'port' in config else 22
        self.user =  config['user'] if 'user' in config else os.getlogin()
        self.key = config['key'] if 'key' in config else '~/.ssh/id_rsa'
        self.path =  config['path'] if 'path' in config else '/'
        self.passphrase = config['passphrase'] if 'passphrase' in config else None
        self.location = '{}:{}{}'.format(self.host, self.port, self.path)
        if(self.path[-1] != '/'):
            self.path += '/'
        self.stats = None
        self.block_size = config['BlockSize']
        self.use_hash = config['UseHash'] if 'UseHash' in config else ''

        print("""bashftp module initialized:
  host: {}
  port: {}
  path: {}
  user: {}
  key: {}
  UseHash: {}""".format(self.host, self.port, self.path, self.user, self.key, self.use_hash))

    def _rlist(self, path):
        rval = []
        args = [
            'ssh', '-C',
            '-i', self.key,
            '-p', str(self.port),
            '{}@{}'.format(self.user, self.host),
            """bashftp ls '{}' {}""".format(path, self.use_hash)
        ]
        # check=False because stuff like lost+found messes with us
        raw = subprocess.run(args,
                env=os.environ,
                check=False,
                stdout=subprocess.PIPE).stdout
        lines = [l for l in raw.decode('utf-8').split("\n") if (len(l) > 0)]

        refile = re.compile("f (\d+) (\d+) ([^ ]+) (.*)")
        redir = re.compile("d (\d+) (.*)")
        for l in lines:
            mm = refile.match(l)
            if(mm):
                self.stats[mm[4]] = {
                    'sz': int(mm[2]),
                    'tm': int(mm[1]),
                    'hash': mm[3]
                }
                rval += [mm[4]]
            else:
                mm = redir.match(l)
                if(mm):
                    more = self._rlist(mm[2])    
                    rval += more
        return rval

    def tree(self):
        self.stats = {}
        if(self.path[-1] != '/'):
            raise Exception('self.path should have ended in /!')
        skip = len(self.path)
        return [s[skip:] for s in self._rlist(self.path)]

    def stat(self, path):
        if(path[-1] == '/'):
            raise 'did not expect path to end in /'
        fp = '{}{}'.format(self.path, path)
        if(self.stats is not None):
            if fp not in self.stats:
                raise Exception('file {} does not exist'.format(fp))
            return self.stats[fp]['sz'], datetime.fromtimestamp(self.stats[fp]['tm']), self.stats[fp]['hash']

        raw = subprocess.check_output(['ssh', '-C',
            '-i', self.key,
            '-p', str(self.port),
            '{}@{}'.format(self.user, self.host),
            """bashftp ls '{}' {}""".format(os.path.dirname(fp), self.use_hash)],
            env=os.environ)
        lines = [l for l in raw.decode('utf-8').split("\n") if (len(l) > 0)]

        rr = re.compile("f (\d+) (\d+) ([^ ]+) (.*)")
        for l in lines:
            mm = rr.match(l)
            if(mm is not None):
                if(mm[4] == fp):
                    return int(mm[2]), datetime.fromtimestamp(int(mm[1])), mm[3]
        
        raise Exception('file {} does not exist'.format(fp))

    def open(self, path):
        return FileHandle(self, path)

    def _remoteexists(self, fullpath):
        return os.path.exists(fullpath)

    def rename(self, path):
        i = 1
        renfro = '{}{}'.format(self.path, path)
        while(self._remoteexists('{}.{}'.format(renfro, i))):
            i += 1
        rento = '{}.{}'.format(renfro, i)

        # FIXME Either add mv to bashftp or change the semantics here...
        print('will rename {} to {}'.format(renfro, rento))
        _ = subprocess.check_output([
                'ssh', '-C',
                '-i', self.key,
                '{}@{}'.format(self.user, self.host),
                '-p', str(self.port),
                '''mv '{}' '{}' '''.format(renfro, rento)],
                env=os.environ)

    @classmethod
    def new(cls, config):
        return Module(config)


ModuleFactory.register('bashftp', Module)
