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
Managers for the test list used by the fuzzer
'''
import re
from kitty.core import KittyException


class StartEndList(object):

    def __init__(self, start, end):
        self._start = start
        self._end = end
        self._current = self._start

    def set_last(self, last):
        if self._end is None or (self._end > last):
            self._end = last

    def next(self):
        if self._current < self._end:
            self._current += 1

    def current(self):
        if self._current < self._end:
            return self._current
        return None

    def reset(self):
        self._current = self._start

    def skip(self, count):
        self._current += count

    def get_count(self):
        return self._end - self._start

    def get_progress(self):
        if self.current():
            return self._current - self._start
        else:
            return self.get_count()

    def as_test_list_str(self):
        res = '%d-' % self._start
        if self._end is not None:
            res += '%d' % self._end
        return res


class RangesList(object):

    def __init__(self, ranges_str):
        self._ranges_str = ranges_str
        self._list = []
        self._idx = 0
        self._open_end_start = None
        self._parse()

    def _parse(self):
        '''
        Crazy function to check and parse the range list string
        '''
        if not self._ranges_str:
            self._open_end_start = 0
        else:
            p_single = re.compile(r'(\d+)$')
            p_open_left = re.compile(r'-(\d+)$')
            p_open_right = re.compile(r'(\d+)-$')
            p_closed = re.compile(r'(\d+)-(\d+)$')
            open_left_found = False
            open_right_found = False
            for entry in self._ranges_str.split(','):
                entry = entry.strip()

                # single number
                match = p_single.match(entry)
                if match:
                    self._list.append(int(match.groups()[0]))
                    continue

                # open left
                match = p_open_left.match(entry)
                if match:
                    if open_left_found:
                        raise KittyException('You have two test ranges that start from zero')
                    open_left_found = True
                    end = int(match.groups()[0])
                    self._list.extend(list(range(0, end + 1)))
                    continue

                # open right
                match = p_open_right.match(entry)
                if match:
                    if open_right_found:
                        raise KittyException('You have two test ranges that does not end')
                    open_right_found = True
                    self._open_end_start = int(match.groups()[0])
                    continue

                # closed range
                match = p_closed.match(entry)
                if match:
                    start = int(match.groups()[0])
                    end = int(match.groups()[1])
                    self._list.extend(list(range(start, end + 1)))
                    continue

                # invalid expression
                raise KittyException('Invalid range found: %s' % entry)
            as_set = set(self._list)
            if len(as_set) < len(self._list):
                raise KittyException('Overlapping ranges in range list')
            self._list = sorted(list(as_set))
            if self._open_end_start and len(self._list) and self._list[-1] >= self._open_end_start:
                raise KittyException('Overlapping ranges in range list')

    def set_last(self, last):
        exceeds = False
        if self._open_end_start is not None:
            if last < self._open_end_start:
                exceeds = True
            else:
                self._list.extend(range(self._open_end_start, last + 1))
        else:
            if self._list[-1] > last:
                exceeds = True
        if exceeds:
            raise KittyException('Specified test range exceeds the maximum mutation count')

    def next(self):
        if self._idx < len(self._list):
            self._idx += 1

    def current(self):
        if self._idx < len(self._list):
            return self._list[self._idx]
        return None

    def reset(self):
        self._idx = 0

    def skip(self, count):
        self._idx += count

    def get_count(self):
        return len(self._list)

    def get_progress(self):
        if self.current():
            return self._current - self._start
        else:
            return self.get_count()

    def as_test_list_str(self):
        return self._ranges_str
