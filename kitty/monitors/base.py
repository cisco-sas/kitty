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
This module defines BaseMonitor - the base (abstract) monitor class
'''

import time
from kitty.core.kitty_object import KittyObject
from kitty.data.report import Report
from kitty.core.threading_utils import LoopFuncThread


class BaseMonitor(KittyObject):
    '''
    Base (abstract) monitor class
    '''

    def __init__(self, name, logger=None):
        '''
        :param name: name of the monitor
        :param logger: logger for the monitor (default: None)
        '''
        super(BaseMonitor, self).__init__(name, logger)
        self.report = Report(name)
        self.monitor_thread = None
        self.test_number = None

    def setup(self):
        '''
        Make sure the monitor is ready for fuzzing
        '''
        self._cleanup()
        self.monitor_thread = LoopFuncThread(self._monitor_func)
        self.monitor_thread.start()

    def teardown(self):
        '''
        cleanup the monitor data and
        '''
        self.monitor_thread.stop()
        self.monitor_thread = None

    def pre_test(self, test_number):
        '''
        Called when a test is started

        :param test_number: current test number
        '''
        if not self._is_alive():
            self.setup()
        self._cleanup()
        self.test_number = test_number
        self.report.add('state', 'STARTED')
        self.report.add('start_time', time.time())
        self.report.add('name', self.name)

    def post_test(self):
        '''
        Called when a test is completed, prepare the report etc.
        '''
        self.report.add('state', 'STOPPED')
        self.report.add('stop_time', time.time())

    def _is_alive(self):
        '''
        Check if victim/monitor alive
        '''
        if self.monitor_thread is not None:
            if self.monitor_thread.is_alive():
                return True
        return False

    def _cleanup(self):
        '''
        perform a monitor cleanup
        '''
        self.report = Report(self.name)

    def get_report(self):
        '''
        :return: the monitor's report
        '''
        return self.report

    def _monitor_func(self):
        '''
        Called in a loop in a separate thread (self.monitor_thread).
        '''
        self.not_implemented('_monitor_func')
