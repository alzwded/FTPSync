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
import dateutil.parser
from datetime import datetime
import re
import os
import urllib.parse
from vendor.ftputil.stat import UnixParser
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
            _ = subprocess.run("""curl -I -Q '-DELE {}' {} "{}:{}{}" """.format(
                self.fullpath,
                self.m._format_user(),
                self.m.host,
                self.m.port,
                urllib.parse.quote(self.fullpath)),
                shell=True,
                check=False,
                capture_output=False)
        _ = subprocess.run("""curl --ftp-pasv --ftp-create-dirs -T - {} {} "{}:{}{}" """.format(
                    '-a' if self.offset != 0 else '',
                    #self._format_C(offset), # getting unsupported REST
                    self.m._format_user(),
                    self.m.host,
                    self.m.port,
                    urllib.parse.quote(self.fullpath)),
                shell=True,
                check=True,
                input=data,
                capture_output=True)
        self.offset += len(data)

    def rewind(self):
        self.offset = 0

    def ff(self):
        self.offset, _ = self.m.stat(self.path)
        return self.offset

    def _format_bytes(self, offset):
        toread = FOUR_MEG-1 if offset + FOUR_MEG <= self.sz else self.sz % FOUR_MEG
        start = offset
        end = offset + toread
        return '-r {}-{}'.format(start, end)

    def drain_to(self, sink):
        if(self.sz is None):
            self.sz, _ = self.m.stat(self.path)

        # don't start at 0 in case we're retrying
        offset = sink.offset

        nblocks = self.sz // FOUR_MEG + (1 if ((self.sz % FOUR_MEG) != 0) else 0);
        nblocks -= offset // FOUR_MEG

        while(nblocks > 0):
            print('blocks left {} sz {}'.format(nblocks, self.sz))
            data = subprocess.check_output("""curl --ftp-pasv {} {} "{}:{}{}" """.format(
                        self.m._format_user(),
                        self._format_bytes(offset),
                        self.m.host,
                        self.m.port,
                        urllib.parse.quote(self.fullpath)),
                    shell=True)
            sink.write(offset, data)
            offset += FOUR_MEG
            nblocks -= 1

class Module:
    def __init__(self, config):
        self.host = 'ftp://{}'.format(config['host'])
        if(self.host[-1:] == '/'):
            self.host = self.host[0:-1]
        self.port =  config['port'] if 'port' in config else 21
        self.user =  config['user'] if 'user' in config else None
        self.password =  config['password'] if 'password' in config else None
        self.path =  config['path'] if 'path' in config else '/'
        if(self.path[-1] != '/'):
            self.path += '/'
        self.location = '{}:{}{}'.format(self.host, self.port, self.path)
        self.stats = None
        self.parseLs = config['ParseFTPLs'] == 'yes'

        print("""FTP module initialized:
  host: {}
  port: {}
  path: {}
  user: {}
  password: ********""".format(self.host, self.port, self.path, self.user))

    def _format_user(self):
        if(self.user is None and self.password is None):
            return ''
        if(self.password is None):
            return '-u "{}"'.format(self.user)
        return '-u "{}:{}"'.format(self.user, self.password)

    def _list(self, path):
        if(path[-1] != '/'):
            raise Exception("the path arg to this method should have ended in /, but got {}".format(path))
        raw = subprocess.check_output("""curl --ftp-pasv {} {} "{}:{}{}" """.format(
                '-l' if self.stats is None else '',
                self._format_user(),
                self.host,
                self.port,
                urllib.parse.quote(path)),
                shell=True)
        if self.stats is not None:
            parser = UnixParser()
            stats = [parser.parse_line(s) for s in raw.decode('utf-8').split("\n") if(len(s) > 0)]
            filelist = []
            for s in stats:
                if s._st_name == '.' or s._st_name == '..':
                    continue
                ff = '{}{}'.format(path, s._st_name)
                self.stats[ff] = s
                filelist.append(ff)
            return filelist
        else:
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
        if(self.parseLs):
            self.stats = {}
        if(self.path[-1] != '/'):
            raise Exception('self.path should have ended in /!')
        skip = len(self.path)
        return [s[skip:] for s in self._rlist(self.path)]

    def stat(self, path):
        if(path[-1] == '/'):
            raise 'did not expect path to end in /'
        if(self.stats is not None):
            fp = '{}{}'.format(self.path, path)
            if fp not in self.stats:
                raise Exception('file {} does not exist'.format(fp))
            return self.stats[fp].st_size, datetime.fromtimestamp(self.stats[fp].st_mtime)
        # TODO be resilient and log errors to a log file
        lines = subprocess.check_output("""curl -I --ftp-pasv {} "{}:{}{}" """.format(
                self._format_user(),
                self.host,
                self.port,
                urllib.parse.quote('{}{}'.format(self.path, path))),
                shell=True).decode('utf-8').split("\n")
        
        #Last-Modified: Wed, 13 Nov 2019 20:20:03 GMT
        #Content-Length: 4011
        #Accept-ranges: bytes
        reSIZE = re.compile('Content-Length: (\d+)')
        reTIME = re.compile('Last-Modified: (.+)')
        sz = None
        tm = None
        for line in lines:
            maSIZE = re.match(reSIZE, line)
            if(maSIZE is not None):
                sz = int(maSIZE[1])
                continue

            maTIME = re.match(reTIME, line)
            if(maTIME is not None):
                tm = dateutil.parser.parse(maTIME[1])
                continue

        print('ftp: ' + repr(('{}{}'.format(self.path, path), sz, tm)))
        return sz, tm

    def open(self, path):
        return FileHandle(self, path)

    def rename(self, path):
        if(path[-1] == '/'):
            raise Exception('{} ending in / was unexpected'.format(path))
        fullpath = '{}{}'.format(self.path, path)
        d = '{}/'.format(os.path.dirname(fullpath))
        localfiles = set(self._list(d))
        i = 1
        while('{}{}.{}'.format(self.path, path, i) in localfiles):
            i += 1
        renfro = '{}{}'.format(self.path, path)
        rento = '{}{}.{}'.format(self.path, path, i)

        print('will rename {} to {}'.format(renfro, rento))

        _ = subprocess.check_output("""curl -v -I {} -Q '-RNFR {}' -Q '-RNTO {}' --ftp-create-dirs "{}:{}/" """.format(
                    self._format_user(),
                    renfro[1:],
                    rento[1:],
                    self.host,
                    self.port,
                    self.path),
                shell=True)

    @classmethod
    def new(cls, config):
        return Module(config)

ModuleFactory.register('ftp', Module)
