# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Kitty.
#
# Kitty is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Kitty is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Kitty.  If not, see <http://www.gnu.org/licenses/>.

'''
EmptyController does nothing, implements both client and server controller
API
'''
from kitty.controllers.client import ClientController


class EmptyController(ClientController):
    '''
    EmptyController does nothing, implements both client and server controller
    API
    '''

    def __init__(self, name='EmptyController', logger=None):
        super(EmptyController, self).__init__(name=name, logger=logger, victim_alive_check_delay=0.3)

    def trigger(self):
        '''
        Trigger a data exchange from the tested client
        '''
        pass
