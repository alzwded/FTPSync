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
import dateutil.parser
from lib.factory import ModuleFactory

class Module:
    def __init__(self, config):
      self.path = os.path.abspath(config['path'])
      if(self.path[-1] != '/'):
        self.path += '/'
      print("""FILE module initialized:
  path={}""".format(self.path))

    def tree(self):
        result = subprocess.run(['find', '.', '-type', 'f'], stdout=subprocess.PIPE, cwd=self.path, check=True)
        expression = re.compile('^\.\/')
        files = [re.sub(expression, '', s) for s in result.stdout.decode('utf-8').split("\n") if len(s) > 0]
        return files

    def stat(self, path):
        sz = int(subprocess.check_output(['stat', '--format', '%s', '{}{}'.format(self.path, path)]).decode('utf-8'))
        tm = dateutil.parser.parse(subprocess.check_output(['stat', '--format', '%y', '{}{}'.format(self.path, path)]).decode('utf-8'))
        return sz, tm

    @classmethod
    def new(cls, config):
        return Module(config)

ModuleFactory.register('file', Module)
