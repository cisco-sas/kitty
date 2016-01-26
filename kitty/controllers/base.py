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
The controller is in charge of preparing the victim for the test.
It should make sure that the victim is in an appropriate state before
the target initiates the transfer session. Sometimes it means doing nothing,
other times it means starting or reseting a VM, killing a process
or performing a hard reset to the victim hardware.
Since the controller is reponsible for the state of the victim,
it is expected to perform a basic monitoring as well, and report whether
the victim is ready for the next test.
'''
import time
from kitty.core.kitty_object import KittyObject
from kitty.data.report import Report


class BaseController(KittyObject):
    '''
    Base class for controllers. Defines basic variables and implements basic behavior.
    '''

    def __init__(self, name, logger=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        '''
        super(BaseController, self).__init__(name, logger)
        self.report = None
        self.test_number = 0

    def setup(self):
        '''
        Called at the beginning of the fuzzing session.
        You should override it with the actual implementation of victim setup.
        '''
        pass

    def teardown(self):
        '''
        Called at the end of the fuzzing session.
        You should override it with the actual implementation of victim teardown.
        '''
        pass

    def pre_test(self, test_number):
        '''
        Called before a test is started. Call super if overriden.

        :param test_number: current test number
        '''
        self.report = Report(self.name)
        self.report.add('start_time', time.time())
        self.test_number = test_number

    def post_test(self):
        '''
        Called when test is done. Call super if overriden.
        '''
        self.report.add('stop_time', time.time())

    def get_report(self):
        '''
        :rtype: :class:`~kitty.data.report.Report`
        :return: a report about the victim since last call to pre_test
        '''
        return self.report
