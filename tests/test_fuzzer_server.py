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
import time
import os

from kitty.model import Template, GraphModel, String, UInt32
from kitty.fuzzers import ServerFuzzer
from kitty.interfaces.base import EmptyInterface
from mocks.mock_target import ServerTargetMock

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
        if self.session_file_name:
            if os.path.exists(self.session_file_name):
                os.remove(self.session_file_name)

    def prepare(self):
        self.start_index = 10
        self.end_index = 20
        self.delay_duration = 0
        self.session_file_name = None

        self.interface = EmptyInterface()

        self.model = GraphModel()
        self.model.logger = self.logger
        self.model.connect(self.t_str)

        self.target = ServerTargetMock({}, logger=self.logger)

        self.fuzzer = ServerFuzzer(name="TestServerFuzzer", logger=self.logger)
        self.fuzzer.set_interface(self.interface)
        self.fuzzer.set_model(self.model)
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

    def testCommandLineArgumentDelay(self):
        self.delay_duration = 0.1
        cmd_line = '--delay=%s' % self.delay_duration
        self.fuzzer = ServerFuzzer(name="TestServerFuzzer", logger=self.logger, option_line=cmd_line)
        self.fuzzer.set_interface(self.interface)
        self.fuzzer.set_model(self.model)
        self.fuzzer.set_target(self.target)
        self.fuzzer.set_range(self.start_index, self.end_index)
        self.assertEqual(self.delay_duration, self.fuzzer.config.delay_secs)
        start_time = time.time()
        self.fuzzer.start()
        end_time = time.time()
        expected_runtime = self.delay_duration * (self.end_index - self.start_index + 1)
        actual_runtime = end_time - start_time
        self.assertAlmostEqual(int(actual_runtime), int(expected_runtime))

    def testCommandLineArgumentSession(self):
        self.session_file_name = 'mysession.sqlite'
        cmd_line = '--session=%s' % self.session_file_name
        self.fuzzer = ServerFuzzer(name="TestServerFuzzer", logger=self.logger, option_line=cmd_line)
        self.fuzzer.set_interface(self.interface)
        self.fuzzer.set_model(self.model)
        self.fuzzer.set_target(self.target)
        self.fuzzer.set_delay_between_tests(self.delay_duration)
        self.fuzzer.set_range(self.start_index, self.end_index)
        self.assertEqual(self.session_file_name, self.fuzzer.config.session_file_name)
        self.fuzzer.start()

    def testVanilla(self):
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        # reports = self.fuzzer._get_reports_manager()
        # self.assertEqual(len(reports), 0)
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, None)
        # self.assertEqual(info.original_start_index, 10)
        self.assertEqual(info.start_index, self.start_index)
        self.assertEqual(info.end_index, self.end_index)

    def testStartingFromStartIndex(self):
        start_index = self.model.num_mutations() - 2
        self.fuzzer.set_range(start_index)
        self.fuzzer.start()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.current_index, None)
        self.assertEqual(info.end_index, self.model.last_index())

    def testEndingAtEndIndex(self):
        start_index = 0
        end_index = 3
        self.fuzzer.set_range(start_index, end_index)
        self.fuzzer.start()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, 3)
        self.assertEqual(info.current_index, None)

    def testFullMutationRange(self):
        self.fuzzer.set_range()
        self.fuzzer.start()

        info = self.fuzzer._get_session_info()
        self.assertEqual(info.start_index, 0)
        self.assertEqual(info.end_index, self.model.last_index())
        self.assertEqual(info.current_index, None)

    def _MOVE_TO_TARGET_TESTS_test_send_failure(self):
        config = {
            '12': {
                'send': {"raise exception": True}
            }
        }
        send_error_target = ServerTargetMock(config, logger=self.logger)
        self.fuzzer.set_target(send_error_target)
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer._get_reports_manager()
        self.assertEqual(len(reports), 1)
        self.assertTrue(12 in reports)
        self.assertEqual(info.failure_count, 1)

    def testTestFailedWhenReportIsFailed(self):
        config = {
            '13': {
                'report': {
                    'status': 'failed', 'reason': 'failure reason'
                }
            }
        }
        target = ServerTargetMock(config, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        self.assertEqual(reports, [int(x) for x in config.keys()])
        self.assertEqual(info.failure_count, len(config))

    def testAllFailedTestsHaveReports(self):
        config = {
            '10': {'report': {'status': 'failed', 'reason': 'failure reason'}},
            '11': {'report': {'status': 'failed', 'reason': 'failure reason'}},
            '12': {'report': {'status': 'failed', 'reason': 'failure reason'}},
            '13': {'report': {'status': 'failed', 'reason': 'failure reason'}}
        }
        target = ServerTargetMock(config, logger=self.logger)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
        info = self.fuzzer._get_session_info()
        reports = self.fuzzer.dataman.get_report_test_ids()
        self.assertEqual(reports, sorted([int(x) for x in config.keys()]))
        self.assertEqual(info.failure_count, len(config))

    def testStoringAllReportsWhenStoreAllReportsIsSetToTrue(self):
        config = {}
        target = ServerTargetMock(config, logger=self.logger)
        self.fuzzer.set_store_all_reports(True)
        self.fuzzer.set_target(target)
        self.fuzzer.start()
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
        info = self.fuzzer._get_session_info()
        self.assertEqual(info.failure_count, 0)
        self.assertEqual(info.current_index, None)
        self.assertEqual(info.start_index, start_index)
        self.assertEqual(info.end_index, expected_end_index)

    def testCallbackIsCalledBetweenTwoNodes(self):
        template1 = Template(name='template1', fields=String('str1'))
        template2 = Template(name='template2', fields=String('str2'))
        self.cb_call_count = 0

        def t1_t2_cb(fuzzer, edge, response):
            self.assertEqual(fuzzer, self.fuzzer)
            self.assertEqual(edge.src, template1)
            self.assertEqual(edge.dst, template2)
            self.cb_call_count += 1

        model = GraphModel()
        model.logger = self.logger
        model.connect(template1)
        model.connect(template1, template2, t1_t2_cb)
        self.model = model
        self.fuzzer.set_model(model)
        self.fuzzer.set_range()
        self.fuzzer.start()
        self.assertEqual(template2.num_mutations(), self.cb_call_count)

    def testCorrectCallbackIsCalledForEachEdge(self):
        template1 = Template(name='template1', fields=String('str1'))
        template2 = Template(name='template2', fields=String('str2'))
        template3 = Template(name='template3', fields=String('str3'))
        self.cb2_call_count = 0
        self.cb3_call_count = 0

        def t1_t2_cb(fuzzer, edge, response):
            self.assertEqual(fuzzer, self.fuzzer)
            self.assertEqual(edge.src, template1)
            self.assertEqual(edge.dst, template2)
            self.cb2_call_count += 1

        def t1_t3_cb(fuzzer, edge, response):
            self.assertEqual(fuzzer, self.fuzzer)
            self.assertEqual(edge.src, template1)
            self.assertEqual(edge.dst, template3)
            self.cb3_call_count += 1

        model = GraphModel()
        model.logger = self.logger
        model.connect(template1)
        model.connect(template1, template2, t1_t2_cb)
        model.connect(template1, template3, t1_t3_cb)
        self.model = model
        self.fuzzer.set_model(model)
        self.fuzzer.set_range()
        self.fuzzer.start()
        self.assertEqual(template2.num_mutations(), self.cb2_call_count)
        self.assertEqual(template3.num_mutations(), self.cb3_call_count)

    def testCorrectCallbackIsCalledForAllEdgesInPath(self):
        template1 = Template(name='template1', fields=String('str1'))
        template2 = Template(name='template2', fields=String('str2'))
        template3 = Template(name='template3', fields=String('str3'))
        self.cb2_call_count = 0
        self.cb3_call_count = 0

        def t1_t2_cb(fuzzer, edge, response):
            self.assertEqual(fuzzer, self.fuzzer)
            self.assertEqual(edge.src, template1)
            self.assertEqual(edge.dst, template2)
            self.cb2_call_count += 1

        def t2_t3_cb(fuzzer, edge, response):
            self.assertEqual(fuzzer, self.fuzzer)
            self.assertEqual(edge.src, template2)
            self.assertEqual(edge.dst, template3)
            self.cb3_call_count += 1

        model = GraphModel()
        model.logger = self.logger
        model.connect(template1)
        model.connect(template1, template2, t1_t2_cb)
        model.connect(template2, template3, t2_t3_cb)
        self.model = model
        self.fuzzer.set_model(model)
        self.fuzzer.set_range()
        self.fuzzer.start()
        self.assertEqual(template2.num_mutations() + template3.num_mutations(), self.cb2_call_count)
        self.assertEqual(template3.num_mutations(), self.cb3_call_count)
