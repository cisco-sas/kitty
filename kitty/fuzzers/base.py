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

import sys
import time
import traceback
import shlex
import docopt
from threading import Event
from kitty.core import KittyException, KittyObject
from kitty.data.data_manager import DataManager, SessionInfo
from kitty.data.report import Report
from pkg_resources import get_distribution


class _Configuration:

    def __init__(self, delay_secs, store_all_reports, session_file_name, max_failures):
        self.delay_secs = delay_secs
        self.store_all_reports = store_all_reports
        self.session_file_name = session_file_name
        self.max_failures = max_failures


def _get_current_version():
    package_name = 'kittyfuzzer'
    current_version = get_distribution(package_name).version
    return current_version


class BaseFuzzer(KittyObject):
    '''
    Common members and logic for client and server fuzzers.
    This class should not be instantiated, only subclassed.
    '''

    def __init__(self, name='', logger=None, option_line=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        :param option_line: cmd line options to the fuzzer (dafult: None)
        '''
        super(BaseFuzzer, self).__init__(name, logger)
        # session to fuzz
        self.model = None
        self.dataman = None
        self.session_info = SessionInfo()
        self.config = _Configuration(
            delay_secs=0,
            store_all_reports=False,
            session_file_name=None,
            max_failures=None,
        )
        # user interface
        self.user_interface = None
        # target
        self.target = None
        # event to implement pause / continue
        self._continue_event = Event()
        self._continue_event.set()
        self._fuzz_path = None
        self._fuzz_node = None
        self._last_payload = None
        self._skip_env_test = False
        self._in_environment_test = True
        self._handle_options(option_line)

    def _handle_options(self, option_line):
        '''
        Handle options from command line, in docopt style.
        This allows passing arguments to the fuzzer from the command line
        without the need to re-write it in each runner.

        :param option_line: string with the command line options to be parsed.
        '''
        if option_line is not None:
            usage = '''
            These are the options to the kitty fuzzer object, not the options to the runner.

            Usage:
                fuzzer [options]

            Options:
                -d --delay <delay>              delay between tests in secodes, float number
                -e --end <end-index>            fuzzing end index, ignored if session-file loaded
                -f --session <session-file>     session file name to use
                -s --start <start-index>        fuzzing start index, ignored if session-file loaded
                -n --no-env-test                don't perform environment test before the fuzzing session
            '''
            options = docopt.docopt(usage, shlex.split(option_line))
            s = options['--start']
            s = 0 if s is None else int(s)
            e = options['--end']
            e = e if e is None else int(e)
            if (s is not None) or (e is not None):
                self.set_range(s, e)
            session_file = options['--session']
            if session_file is not None:
                self.set_session_file(session_file)
            delay = options['--delay']
            if delay is not None:
                self.set_delay_between_tests(float(delay))
            skip_env_test = options['--no-env-test']
            if skip_env_test:
                self._skip_env_test = True

    def set_skip_env_test(self, skip_env_test=True):
        '''
        Set whether to skip the environment test.
        Call this if the environment test cannot pass
        and you prefer to start the tests without it.

        :param skip_env_test: skip the environment test (default: True)
        '''
        self._skip_env_test = skip_env_test

    def set_delay_duration(self, delay_duration):
        '''
        .. deprecated::
            use :func:`~kitty.fuzzers.base.BaseFuzzer.set_delay_between_tests`
        '''
        raise NotImplementedError('API was changed, use set_delay_between_tests')

    def set_delay_between_tests(self, delay_secs):
        '''
        Set duration between tests

        :param delay_secs: delay between tests (in seconds)
        '''
        self.config.delay_secs = delay_secs
        return self

    def set_store_all_reports(self, store_all_reports):
        '''
        :param store_all_reports: should all reports be stored
        '''
        self.config.store_all_reports = store_all_reports
        return self

    def set_session_file(self, filename):
        '''
        Set session file name, to keep state between runs

        :param filename: session file name
        '''
        self.config.session_file_name = filename
        return self

    def set_model(self, model):
        '''
        Set the model to fuzz

        :type model: :class:`~kitty.model.high_level.base.BaseModel` or a subclass
        :param model: Model object to fuzz
        '''
        self.model = model
        if self.model:
            self.model.set_notification_handler(self)
            self.handle_stage_changed(model)
        return self

    def set_target(self, target):
        '''
        :param target: target object
        '''
        self.target = target
        if target:
            self.target.set_fuzzer(self)
        return self

    def set_max_failures(self, max_failures):
        '''
        :param max_failures: maximum failures before stopping the fuzzing session
        '''
        self.config.max_failures = max_failures
        return self

    def set_range(self, start_index=0, end_index=None):
        '''
        Set range of tests to run

        :param start_index: index to start at (default=0)
        :param end_index: index to end at(default=None)
        '''
        self.session_info.start_index = start_index
        self.session_info.current_index = start_index
        self.session_info.end_index = end_index
        return self

    def set_interface(self, interface):
        '''
        :param interface: user interface
        '''
        self.user_interface = interface
        return self

    def _check_session_validity(self):
        current_version = _get_current_version()
        if current_version != self.session_info.kitty_version:
            raise KittyException('kitty version in stored session (%s) != current kitty version (%s)' % (
                current_version,
                self.session_info.kitty_version))
        model_hash = self.model.hash()
        if model_hash != self.session_info.data_model_hash:
            raise KittyException('data model hash in stored session(%s) != current data model hash (%s)' % (
                model_hash,
                self.session_info.data_model_hash
            ))

    def start(self):
        '''
        start the fuzzing session
        '''
        assert(self.model)
        assert(self.user_interface)
        assert(self.target)

        if self._load_session():
            self._check_session_validity()
        else:
            self.session_info.kitty_version = _get_current_version()
            # TODO: write hash for high level
            self.session_info.data_model_hash = self.model.hash()
        if self.session_info.end_index is None:
            self.session_info.end_index = self.model.last_index()
        self._store_session()
        if self.session_info.start_index > self.session_info.current_index:
            self.session_info.current_index = self.session_info.start_index

        self.set_signal_handler()
        self.user_interface.set_data_provider(self.dataman)
        self.user_interface.set_continue_event(self._continue_event)
        self.user_interface.start()

        self.session_info.start_time = time.time()
        try:
            self._start_message()
            self.target.setup()
            start_index = self.session_info.current_index
            if self._skip_env_test:
                self.logger.info('Skipping environment test')
            else:
                self.logger.info('Performing environment test')
                self._test_environment()
            self._in_environment_test = False
            self.session_info.current_index = start_index
            self.model.skip(self.session_info.current_index)
            self._start()
            return True
        except Exception as e:
            self.logger.error('Error occurred while fuzzing: %s', repr(e))
            self.logger.error(traceback.format_exc())
            return False

    def handle_stage_changed(self, model):
        '''
        handle a stage change in the data model

        :param model: the data model that was changed
        '''
        stages = model.get_stages()
        if self.dataman:
            self.dataman.set('stages', stages)

    def _test_environment(self):
        '''
        Test that the environment is ready to run.
        Should be implemented by subclass
        '''
        raise NotImplementedError('should be implemented by subclass')

    def _start(self):
        self.not_implemented('_start')

    def _update_test_info(self):
        test_info = self.model.get_test_info()
        self.dataman.set('test_info', test_info)
        template_info = self.model.get_template_info()
        self.dataman.set('template_info', template_info)

    def _pre_test(self):
        self._update_test_info()
        self.session_info.current_index = self.model.current_index()
        self.target.pre_test(self.model.current_index())

    def _post_test(self):
        '''
        :return: True if test failed
        '''
        failure_detected = False
        self.target.post_test(self.model.current_index())
        report = self._get_report()
        status = report.get_status()
        if self._in_environment_test:
            return status != Report.PASSED
        if status != Report.PASSED:
            self._store_report(report)
            self.user_interface.failure_detected()
            failure_detected = True
            self.logger.warn('!! Failure detected !!')
        elif self.config.store_all_reports:
            self._store_report(report)
        if failure_detected:
            self.session_info.failure_count += 1
        self._store_session()
        if self.config.delay_secs:
            self.logger.debug('delaying for %f seconds', self.config.delay_secs)
            time.sleep(self.config.delay_secs)
        return failure_detected

    def _get_report(self):
        report = self.target.get_report()
        return report

    def _start_message(self):
        self.logger.info('''
                 --------------------------------------------------
                 Starting fuzzing session
                 Target: %s
                 UI: %s

                 Total possible mutation count: %d
                 Fuzzing the mutation range: %d to %d
                 --------------------------------------------------
                                 Happy hacking
                 --------------------------------------------------
                         ''',
                         self.target.get_description(),
                         self.user_interface.get_description(),
                         self.model.num_mutations(),
                         self.session_info.current_index,
                         self.session_info.end_index
                         )

    def _end_message(self):
        tested = max(0, self.model.current_index() - self.session_info.start_index + 1)
        self.logger.info('''
                         --------------------------------------------------
                         Finished fuzzing session
                         Target: %s

                         Tested %d mutation%s
                         Mutation range: %d to %d
                         Failure count: %d
                         --------------------------------------------------
                         ''',
                         self.target.get_description(),
                         tested,
                         's' if tested > 1 else '',
                         self.session_info.start_index,
                         self.model.current_index(),
                         self.session_info.failure_count
                         )

    def _test_info(self):
        self.logger.info('----------------------------------------------')
        fuzz_node_info = self.model.get_test_info()
        keys = sorted(fuzz_node_info.keys())
        key_max_len = 0
        for key in keys:
            if len(key) > key_max_len:
                key_max_len = len(str(key))
        for k in keys:
            v = str(fuzz_node_info[k])
            k = str(k)
            pad = ' ' * (key_max_len - len(k) + 1)
            if len(v) > 70:
                v = v[:70] + '...'
            self.logger.info('%s:%s%s' % (k, pad, v))
        self.logger.info('----------------------------------------------')

    def _check_pause(self):
        if not self._continue_event.is_set():
            self.logger.info('fuzzer paused, waiting for resume command from user')
            self._continue_event.wait()
            self.logger.info('resume command received, continue running')

    def stop(self):
        '''
        stop the fuzzing session
        '''
        assert(self.model)
        assert(self.user_interface)
        assert(self.target)
        self.user_interface.stop()
        self.target.teardown()
        self.dataman.submit_task(None)
        self.unset_signal_handler()

    def _store_report(self, report):
        self.logger.debug('<in>')
        report.add('test_number', self.model.current_index())
        report.add('fuzz_path', self.model.get_sequence_str())
        test_info = self.model.get_test_info()
        data_model_report = Report(name='Data Model')
        for k, v in test_info.items():
            data_model_report.add(k, v)
        report.add(data_model_report.get_name(), data_model_report)
        payload = self._last_payload
        if payload is not None:
            data_report = Report('payload')
            data_report.add('raw', payload)
            data_report.add('hex', payload.encode('hex'))
            data_report.add('length', len(payload))
            report.add('payload', data_report)
        else:
            report.add('payload', None)

        self.dataman.store_report(report, self.model.current_index())
        self.dataman.get_report_by_id(self.model.current_index())

    def _store_session(self):
        self._set_session_info()

    def _get_session_info(self):
        info = self.dataman.get_session_info()
        return info

    def _get_test_info(self):
        info = self.dataman.get('test_info')
        return info

    def _set_session_info(self):
        self.dataman.set_session_info(self.session_info)
        self.dataman.set('fuzzer_name', self.get_name())
        self.dataman.set('session_file_name', self.config.session_file_name)

    def _load_session(self):
        if not self.config.session_file_name:
            self.config.session_file_name = ':memory:'
        self.dataman = DataManager(self.config.session_file_name)
        self.dataman.start()
        if self.model:
            self.handle_stage_changed(self.model)
        info = self._get_session_info()
        if info:
            self.logger.info('Loaded session from DB')
            self.session_info = info
            return True
        else:
            self.logger.info('No session loaded')
            self._set_session_info()
            return False

    def _exit_now(self, signal, frame):
        self.stop()
        sys.exit(0)

    def _keep_running(self):
        '''
        Should we still fuzz??
        '''
        if self.config.max_failures:
            if self.session_info.failure_count >= self.config.max_failures:
                return False
        return self.model.current_index() < self.session_info.end_index

    def set_signal_handler(self):
        '''
        Replace the signal handler with self._exit_now
        '''
        import signal
        signal.signal(signal.SIGINT, self._exit_now)

    def unset_signal_handler(self):
        '''
        Set the default signal handler
        '''
        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)
