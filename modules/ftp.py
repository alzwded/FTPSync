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
import re

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

        print("""FTP module initialized:
  host: {}
  port: {}
  path: {}
  user: {}
  password: {}""".format(self.host, self.port, self.path, self.user, self.password))

    def _format_user(self):
        if(self.user is None and self.password is None):
            return ''
        if(self.password is None):
            return '-u "{}"'.format(self.user)
        return '-u "{}:{}"'.format(self.user, self.password)

    def _list(self, path):
        if(path[-1] != '/'):
            raise Exception("the path arg to this method should have ended in /, but got {}".format(path))
        raw = subprocess.check_output("""curl --ftp-pasv -l {} "{}:{}{}" """.format(
                self._format_user(),
                self.host,
                self.port,
                path),
                shell=True)
        return ["{}{}".format(path, s) for s in raw.decode('utf-8').split("\n") if len(s) > 0]

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
        # TODO be resilient and log errors to a log file
        lines = subprocess.check_output("""curl -I --ftp-pasv {} "{}:{}{}{}" """.format(
                self._format_user(),
                self.host,
                self.port,
                self.path,
                path),
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

        return sz, tm
        

def new(config):
    return Module(config)
