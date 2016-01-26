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

from kitty.core import KittyException
import types


def is_of_types(obj, types):
    '''
    :param obj: object to assert
    :param types: iterable of types, or a signle type
    :raise: an exception if obj is not an instance of types
    '''
    if not isinstance(obj, types):
        raise KittyException('object type (%s) is not one of (%s)' % (type(obj), types))


def is_int(obj):
    '''
    :param obj: object to assert
    :raise: an exception if obj is not an int type
    '''
    is_of_types(obj, types.IntType)


def is_in(obj, it):
    '''
    :param obj: object to assert
    :param it: iterable of elements we assert obj is in
    :raise: an exception if obj is in an iterable
    '''
    if obj not in it:
        raise KittyException('(%s) is not in %s' % (obj, it))


def not_none(obj):
    '''
    :param obj: object to assert
    :raise: an exception if obj is not None
    '''
    if obj is None:
        raise KittyException('object is None')
