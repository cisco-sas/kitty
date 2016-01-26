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

from mock_config import Config
from kitty.targets.server import ServerTarget
from kitty.data.report import Report


class TargetMock(ServerTarget):

    def __init__(self, config=None):
        super(TargetMock, self).__init__('MockTarget')
        self.config = Config('target', config).get_config_dict()

    def _restart(self):
        pass

    def get_key_for_test(self, test_number, key):
        #self.logger.debug('get_key_for_test. our dictionary: %s', self.config)
        res = None
        test_number = str(test_number)
        if test_number in self.config:
            if key in self.config[test_number]:
                res = self.config[test_number][key]
        elif 'always' in self.config:
            if key in self.config['always']:
                res = self.config['always'][key]
        return res

    def _send_to_target(self, data):
        config_send = self.get_key_for_test(self.test_number, 'send')
        if config_send:
            if 'raise exception' in config_send:
                raise Exception('Mock exception from send')

    def _receive_from_target(self):
        res = ''
        config_send = self.get_key_for_test(self.test_number, 'receive')
        if config_send:
            if 'raise exception' in config_send:
                raise Exception('Mock exception from receive')
        return res

    def get_report(self):
        self.logger.debug('TargetMock.get_report called for test %d' % self.test_number)
        report = self.report
        config_report = self.get_key_for_test(self.test_number, 'report')
        if config_report:
            self.logger.debug('found matching config: %s', repr(config_report))
            for k, v in config_report.iteritems():
                report.add(k, v)
        return report

    def setup(self):
        self.logger.debug('target.setup called')

    def teardown(self):
        self.logger.debug('target.teardown called')

    def pre_test(self, test_num):
        self.logger.debug('target.post_test called')
        self.test_number = test_num
        self.report = Report(self.name)

    def post_test(self, test_num):
        self.logger.debug('target.post_test called')

    def failure_detected(self):
        return False
