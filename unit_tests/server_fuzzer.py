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

import unittest
import logging

from kitty.model import Template, GraphModel, String, UInt32
from kitty.fuzzers import ServerFuzzer
from kitty.interfaces.base import EmptyInterface
from mocks.mock_target import TargetMock

test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('TestServerFuzzer')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] -> %(message)s')
        handler = logging.FileHandler('logs/test_server_fuzzer.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


class TestServerFuzzer(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)

        self.t_str = Template(name='simple_str_template', fields=[String(name='str1', value='kitty')])

        self.t_int = Template(name='simple_int_template', fields=[UInt32(name='int1', value=0x1234)])
        self.fuzzer = None
        self.prepare()

    def tearDown(self):
        if self.fuzzer:
            self.fuzzer.stop()

    def prepare(self):
        self.start_index = 10
        self.end_index = 20
        self.delay_duration = 0
        self.fuzzer = ServerFuzzer(name="TestServerFuzzer", logger=self.logger)

        self.interface = EmptyInterface()
        self.fuzzer.set_interface(self.interface)

        self.model = GraphModel()

        self.model.connect(self.t_str)
        self.fuzzer.set_model(self.model)

        self.target = TargetMock({})
        self.fuzzer.set_target(self.target)

        self.fuzzer.set_range(self.start_index, self.end_index)
        self.fuzzer.set_delay_between_tests(self.delay_duration)

    def test_start_without_session(self):
        self.fuzzer.set_model(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def test_start_without_target(self):
        self.fuzzer.set_target(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def test_start_without_interface(self):
        self.fuzzer.set_interface(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def test_vanilla(self):
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        # reports = self.fuzzer._get_reports_manager()
        # self.assertEqual(len(reports), 0)
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, self.end_index)
        # self.assertEqual(info.original_start_index, 10)
        self.assertEqual(info.start_index, self.start_index)
        self.assertEqual(info.end_index, self.end_index)
        mutations_tested = info.current_index - info.start_index
        self.assertEqual(mutations_tested, self.end_index - self.start_index)

    def test_start_index(self):
        start_index = self.model.num_mutations() - 2
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.current_index, self.model.last_index())
        self.assertEqual(info.end_index, self.model.last_index())

    def test_end_index(self):
        start_index = 0
        end_index = 3
        self.fuzzer.set_range(start_index, end_index)
        self.fuzzer.start()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, 3)
        self.assertEqual(info.current_index, 3)

    def test_full_range(self):
        self.fuzzer.set_range()
        self.fuzzer.start()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, self.model.last_index())
        self.assertEqual(info.current_index, self.model.last_index())

    def _MOVE_TO_TARGET_TESTS_test_send_failure(self):
        config = {
            '12': {
                'send': ["raise exception"]
            }
        }
        send_error_target = TargetMock(config)
        self.fuzzer.set_target(send_error_target)
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer._get_reports_manager()
        self.assertEqual(len(reports), 1)
        self.assertTrue(12 in reports)
        self.assertEqual(info.failure_count, 1)

    def ___test_target_failed_is_true(self):
        config = {
            '12': {
                'report': {
                    'failed': False
                }
            },
            '13': {
                'report': {
                    'failed': True
                }
            }
        }
        target = TargetMock(config)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer._get_reports_manager()
        self.assertEqual(len(reports), 1)
        self.assertTrue(13 in reports)
        self.assertEqual(info.failure_count, 1)

    def test_set_range(self):
        start_index = self.model.num_mutations() - 5
        self.model.connect(self.t_str, self.t_int)
        expected_end_index = self.model.last_index()
        expected_num_mutations = expected_end_index - start_index
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, expected_end_index)
        mutations_tested = info.current_index - info.start_index
        self.assertEqual(mutations_tested, expected_num_mutations)
        self.assertEqual(info.start_index, start_index)
        self.assertEqual(info.end_index, expected_end_index)
