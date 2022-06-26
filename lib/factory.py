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

import pkgutil

class ModuleFactory:
    modules = {}

    @classmethod
    def new(cls, config):
        return cls.modules[config['protocol']].new(config)

    @classmethod
    def register(cls, protocol, mod):
        print("Registered {} module".format(protocol))
        cls.modules[protocol] = mod

for _, module, _ in pkgutil.iter_modules(['modules']):
    _ = __import__('modules.{}'.format(module))
