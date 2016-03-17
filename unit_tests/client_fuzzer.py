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
from kitty.fuzzers import ClientFuzzer
from kitty.interfaces.base import EmptyInterface
from mocks.mock_target import ClientTargetMock

test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('TestServerFuzzer')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] -> %(message)s')
        handler = logging.FileHandler('logs/test_client_fuzzer.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


class TestClientFuzzer(unittest.TestCase):

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

    def default_callback(self, stage, resp):
        pass

    def prepare(self):
        self.start_index = 10
        self.end_index = 20
        self.delay_duration = 0
        self.fuzzer = ClientFuzzer(name="TestServerFuzzer", logger=self.logger)

        self.interface = EmptyInterface()
        self.fuzzer.set_interface(self.interface)

        self.model = GraphModel()
        self.model.logger = self.logger

        self.model.connect(self.t_str)
        self.fuzzer.set_model(self.model)

        self.default_config = {
            'always': {
                'trigger': {
                    'fuzzer': self.fuzzer,
                    'stages': [
                        ('simple_str_template', {})
                    ]
                }
            }
        }
        self.target = ClientTargetMock(self.default_config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(self.target)

        self.fuzzer.set_range(self.start_index, self.end_index)
        self.fuzzer.set_delay_between_tests(self.delay_duration)

    def testRaisesExceptionWhenStartedWithoutModel(self):

        self.fuzzer.set_model(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def testRaisesExceptionWhenStartedWithoutTarget(self):
        self.fuzzer.set_target(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def testRaisesExceptionWhenStartedWithoutInterface(self):
        self.fuzzer.set_interface(None)
        self.assertRaises(AssertionError, self.fuzzer.start)
        self.fuzzer = None

    def testVanilla(self):
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
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

    def testStartingFromStartIndex(self):
        start_index = self.model.num_mutations() - 2
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.current_index, self.model.last_index())
        self.assertEqual(info.end_index, self.model.last_index())

    def testEndingAtEndIndex(self):
        start_index = 0
        end_index = 3
        self.fuzzer.set_range(start_index, end_index)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, 3)
        self.assertEqual(info.current_index, 3)

    def testFullMutationRange(self):
        self.fuzzer.set_range()
        self.fuzzer.start()
        self.fuzzer.wait_until_done()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, self.model.last_index())
        self.assertEqual(info.current_index, self.model.last_index())

    def testTestFailedWhenReportIsFailed(self):
        config = {
            '13': {
                'report': {
                    'failed': True
                }
            }
        }
        config.update(self.default_config)
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        self.assertEqual(sorted(reports), sorted([int(x) for x in config.keys() if x != 'always']))
        self.assertEqual(info.failure_count, len(config) - 1)

    def testAllFailedTestsHaveReports(self):
        config = {
            '10': {'report': {'failed': True}},
            '11': {'report': {'failed': True}},
            '12': {'report': {'failed': True}},
            '13': {'report': {'failed': True}}
        }
        config.update(self.default_config)
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        self.assertEqual(sorted(reports), sorted([int(x) for x in config.keys() if x != 'always']))
        self.assertEqual(info.failure_count, len(config) - 1)

    def testStoringAllReportsWhenStoreAllReportsIsSetToTrue(self):
        config = {}
        config.update(self.default_config)
        target = ClientTargetMock(config, self.default_callback, logger=self.logger)
        self.fuzzer.set_store_all_reports(True)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        expected_mutation_count = self.end_index - self.start_index + 1
        expected_failure_count = 0
        self.assertEqual(len(reports), expected_mutation_count)
        self.assertEqual(info.failure_count, expected_failure_count)

    def testOnlyTestsInSetRangeAreExecuted(self):
        start_index = self.model.num_mutations() - 5
        self.model.connect(self.t_str, self.t_int)
        expected_end_index = self.model.last_index()
        expected_num_mutations = expected_end_index - start_index
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()
        self.fuzzer.wait_until_done()
        info = self.fuzzer._get_session_info()
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, expected_end_index)
        mutations_tested = info.current_index - info.start_index
        self.assertEqual(mutations_tested, expected_num_mutations)
        self.assertEqual(info.start_index, start_index)
        self.assertEqual(info.end_index, expected_end_index)
