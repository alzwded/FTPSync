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
import os.path
from datetime import datetime
from lib.factory import ModuleFactory

SEEK_SET = 0
SEEK_POS = 1
SEEK_END = 2

class FileHandle:
    def __init__(self, module, path):
        self.m = module
        self.fullpath = '{}{}'.format(self.m.path, path)
        self.path = path
        self.sz = None
        self.offset = 0

    def rewind(self):
        self.offset = 0

    def ff(self):
        self.offset, _, _ = self.m.stat(self.path)
        return self.offset

    def write(self, offset, data):
        d = os.path.dirname(self.fullpath)
        _ = subprocess.check_output(['mkdir', '-p', d])
        if(offset == 0 and os.path.exists(self.fullpath)):
            os.remove(self.fullpath)
        with open(self.fullpath, 'ab') as f:
            #f.seek(0, SEEK_SET)
            #print('truncating to {}'.format(offset))
            #f.truncate(offset) # WTF this just makes the file full of nulls
            #f.seek(offset, SEEK_SET)
            f.write(data)
            self.offset += len(data)

    def drain_to(self, sink):
        if(self.sz is None):
            self.sz, _, _ = self.m.stat(self.path)

        # don't start at 0 in case we're retrying
        offset = sink.offset

        nblocks = self.sz // self.m.block_size + (1 if ((self.sz % self.m.block_size) != 0) else 0);
        nblocks -= offset // self.m.block_size

        with open(self.fullpath, 'rb') as f:
            while(nblocks > 0):
                print('blocks left {} sz {}'.format(nblocks, self.sz))
                toread = self.m.block_size if offset + self.m.block_size <= self.sz else self.sz % self.m.block_size
                print('writing at offset {}'.format(offset))
                f.seek(offset, SEEK_SET)
                data = f.read(toread)
                sink.write(offset, data)
                offset += len(data)
                nblocks -= 1
        print('Wrote {} out of {}'.format(offset, self.sz))


class Module:
    def __init__(self, config):
      self.path = os.path.abspath(config['path'])
      self.location = 'file://localhost{}'.format(self.path)
      if(self.path[-1] != '/'):
        self.path += '/'
      self.block_size = config['BlockSize']
      print("""FILE module initialized:
  path={}""".format(self.path))

    def tree(self):
        result = subprocess.run(['find', '.', '-type', 'f'], stdout=subprocess.PIPE, cwd=self.path, check=True)
        expression = re.compile('^\.\/')
        files = [re.sub(expression, '', s) for s in result.stdout.decode('utf-8').split("\n") if len(s) > 0]
        return files

    def stat(self, path):
        sz = int(subprocess.check_output(['stat', '-c', '%s', '{}{}'.format(self.path, path)]).decode('utf-8'))
        tm = datetime.fromtimestamp(int(subprocess.check_output(['stat', '-c', '%Y', '{}{}'.format(self.path, path)]).decode('utf-8')))
        print(repr(('{}{}'.format(self.path, path), sz, tm)))
        return sz, tm, ''

    def open(self, path):
        return FileHandle(self, path)

    def rename(self, path):
        i = 1
        while(os.path.exists('{}{}.{}'.format(self.path, path, i))):
            i += 1
        renfro = '{}{}'.format(self.path, path)
        rento = '{}{}.{}'.format(self.path, path, i)

        print('will rename {} to {}'.format(renfro, rento))
        os.rename(renfro, rento)

    @classmethod
    def new(cls, config):
        return Module(config)

ModuleFactory.register('file', Module)
