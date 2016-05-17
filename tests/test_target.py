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
Tests for the target classes
'''
import unittest
import logging
from kitty.targets import BaseTarget
from kitty.core.actor import KittyActorInterface


test_logger = None


def get_test_logger():
    global test_logger
    if test_logger is None:
        logger = logging.getLogger('TestClientFuzzer')
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] -> %(message)s')
        handler = logging.FileHandler('logs/test_target.log', mode='w')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        test_logger = logger
    return test_logger


def count_calls(fn_name):
    def decorator(func):
        def wrap(self, *args, **kwargs):
            if fn_name not in self.call_count:
                self.call_count[fn_name] = 0
            self.call_count[fn_name] += 1
            return func(self, *args, **kwargs)
        return wrap
    return decorator


class TestActor(KittyActorInterface):

    def __init__(self, name, logger=None, victim_alive_check_delay=0.3):
        super(TestActor, self).__init__(name, logger, victim_alive_check_delay)
        self.call_count = {}

    def get_call_count(self, func):
        if func in self.call_count:
            return self.call_count[func]
        return None

    @count_calls('setup')
    def setup(self):
        super(TestActor, self).setup()

    @count_calls('teardown')
    def teardown(self):
        super(TestActor, self).teardown()

    @count_calls('pre_test')
    def pre_test(self, test_number):
        super(TestActor, self).pre_test(test_number)

    @count_calls('post_test')
    def post_test(self):
        super(TestActor, self).post_test()

    @count_calls('get_report')
    def get_report(self):
        return super(TestActor, self).get_report()

    @count_calls('is_victim_alive')
    def is_victim_alive(self):
        return super(TestActor, self).is_victim_alive()


class BaseTargetTests(unittest.TestCase):

    def setUp(self):
        self.logger = get_test_logger()
        self.uut = BaseTarget(name='uut', logger=self.logger)
        self.controller = TestActor('controller', logger=self.logger)
        self.monitor1 = TestActor('Monitor1', logger=self.logger)
        self.monitor2 = TestActor('Monitor2', logger=self.logger)

    def add_actors(self):
        self.uut.set_controller(self.controller)
        self.uut.add_monitor(self.monitor1)
        self.uut.add_monitor(self.monitor2)

    def check_calls(self, func, count):
        self.assertEqual(self.controller.get_call_count(func), 1)
        self.assertEqual(self.monitor1.get_call_count(func), 1)
        self.assertEqual(self.monitor2.get_call_count(func), 1)

    def testCallSetupOfEnclosedActors(self):
        '''
        target.setup() ==> target.[controller, monitors].setup()
        '''
        self.add_actors()
        self.uut.setup()
        self.check_calls('setup', 1)

    def testCallTeardownOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.teardown()
        self.check_calls('teardown', 1)

    def testCallPreTestOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.check_calls('pre_test', 1)

    def testCallPostTestOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        self.check_calls('post_test', 1)

    def testCallGetReportOfEnclosedActors(self):
        self.add_actors()
        self.uut.setup()
        self.uut.pre_test(1)
        self.uut.post_test(1)
        self.uut.get_report()
        self.check_calls('get_report', 1)
