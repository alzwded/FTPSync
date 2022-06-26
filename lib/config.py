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
import configparser

def _invalid_config():
    print("""Example config file:
    [Reference]
    protocol=ftp
    root=/folder1
    host=server.lan
    port=21
    user=johndoe
    password=badpassword

    [Mirror]
    protocol=sftp
    root=~/mirrors/folder1
    host=mars.lan
    port=22
    user=johndoe
    key=~/.ssh/id_rsa
""")
    exit(1)

def parse_config(configpath):
    config = configparser.ConfigParser()
    config.read(configpath)
    if(not config.has_section("Reference") or not config.has_section("Mirror")):
        _invalid_config()

    return (config['Reference'], config['Mirror'])

def parse_commands(commandspath):
    raise Exception('not implemented')
