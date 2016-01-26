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

from threading import Event
from kitty.fuzzers.base import BaseFuzzer
from kitty.core.threading_utils import LoopFuncThread


class ClientFuzzer(BaseFuzzer):
    '''
    ClientFuzzer is designed for fuzzing clients.
    It does not preform an active fuzzing, but rather returns a mutation of a
    response when in the right state.
    It is designed to be a module that is integrated into different stacks.
    See its usage example in the file examples/client_fuzzer_example.py which
    designed to fuzz a browser.
    '''

    #  Wild card for matching any stage
    STAGE_ANY = '******************'

    def __init__(self, name='ClientFuzzer', logger=None, option_line=None):
        '''
        :param name: name of the object
        :param logger: logger for the object (default: None)
        :param option_line: cmd line options to the fuzzer
        '''
        super(ClientFuzzer, self).__init__(name, logger, option_line)
        self._target_control_thread = LoopFuncThread(self._do_trigger)
        self._trigger_stop_evt = Event()
        self._target_control_thread.set_func_stop_event(self._trigger_stop_evt)
        self._index_in_path = 0
        # self._do_fuzz = Event()

    def stop(self):
        '''
        Stop the fuzzing session
        '''
        self.logger.info('Stopping client fuzzer')
        self._target_control_thread.stop()
        self.target.signal_mutated()
        super(ClientFuzzer, self).stop()

    def _pre_test(self):
        super(ClientFuzzer, self)._pre_test()
        # self._do_fuzz.set()

    def _post_test(self):
        super(ClientFuzzer, self)._post_test()

    def _do_trigger(self):
        self.logger.debug('_do_trigger called')
        self._check_pause()
        if self.model.mutate() and self._keep_running():
            self._fuzz_path = self.model.get_sequence()
            self._index_in_path = 0
            self._pre_test()
            self._test_info()
            self.target.trigger()
            self._post_test()
        else:
            self._end_message()
            self._trigger_stop_evt.wait()

    def _start(self):
        self._start_message()
        self.target.setup()
        self._target_control_thread.start()

    def _should_fuzz_node(self, fuzz_node, stage):
        '''
        The matching stage is either the name of the last node, or ClientFuzzer.STAGE_ANY.

        :return: True if we are in the correct model node
        '''
        if stage == ClientFuzzer.STAGE_ANY:
            return True
        if fuzz_node.name.lower() == stage.lower():
            if self._index_in_path == len(self._fuzz_path) - 1:
                return True
        else:
            return False

    def get_mutation(self, stage, data):
        '''
        Get the next mutation, if in the correct stage

        :param stage: current stage of the stack
        :param data: a dictionary of items to pass to the model
        :return: mutated payload if in apropriate stage, None otherwise
        '''
        payload = None
        # Commented out for now: we want to return the same
        # payload - while inside the same test
        # if self._keep_running() and self._do_fuzz.is_set():
        if self._keep_running():
            fuzz_node = self._fuzz_path[self._index_in_path].dst
            if self._should_fuzz_node(fuzz_node, stage):
                fuzz_node.set_session_data(data)
                payload = fuzz_node.render().tobytes()
                self._last_payload = payload
            else:
                self._index_in_path += 1
                if self._index_in_path >= len(self._fuzz_path):
                    self._index_in_path = 0
        if payload:
            self._notify_mutated()
        return payload

    def _notify_mutated(self):
        # self._do_fuzz.clear()
        self.target.signal_mutated()
