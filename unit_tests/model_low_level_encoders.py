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
Tests for low level encoders:
'''
from kitty.model.low_level.encoder import BitFieldMultiByteEncoder
from kitty.model.low_level import BitField
from common import BaseTestCase
from kitty.core import KittyException


class BitFieldMultiByteEncoderTests(BaseTestCase):
    
    def setUp(self, cls=None):
        super(BitFieldMultiByteEncoderTests, self).setUp(cls)

    def _multibyte_len(self, num):
        num_bits = len(bin(num)) -2
        num_bytes = num_bits / 7
        if num_bits % 7 != 0:
            num_bytes +=1
        return num_bytes*8

    def _test(self, bitfield):
        expected_len = self._multibyte_len(bitfield._default_value)
        # bitfield.mutate()
        rendered = bitfield.render()
        self.assertEquals(expected_len, len(rendered))
    
    def test_unsigned_length_8(self):
        bitfield = BitField( 0xaa,
                             length=8,
                             signed=False,
                             max_value=255,
                             encoder=BitFieldMultiByteEncoder()
                            )
        self._test(bitfield)

    def test_unsigned_length_16(self):
        bitfield = BitField( 1234,
                             length=16,
                             signed=False,
                             encoder=BitFieldMultiByteEncoder()
                            )
        self._test(bitfield)

    def test_unsigned_length_32(self):
        bitfield = BitField( 1234,
                             length=32,
                             signed=False,
                             encoder=BitFieldMultiByteEncoder()
                            )
        self._test(bitfield)

    def test_unsigned_length_64(self):
        bitfield = BitField( 78945,
                             length=64,
                             signed=False,
                             encoder=BitFieldMultiByteEncoder()
                            )
        self._test(bitfield)

    def test_unsigned_length_11(self):
        bitfield = BitField( 14,
                             length=11,
                             signed=False,
                             encoder=BitFieldMultiByteEncoder()
                            )
        self._test(bitfield)

    def test_BitFieldMultiByteEncoder_signed__unsupported(self):
        self.assertRaises(KittyException, lambda : BitField( -12,
                             length=8,
                             signed=True,
                             max_value=127,
                             encoder=BitFieldMultiByteEncoder()
                            ))
        

    