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
from Crypto.Cipher import AES
from kitty.model.low_level.encoder import BitFieldMultiByteEncoder
from kitty.model.low_level.encoder import ENC_STR_DEFAULT
from kitty.model.low_level.encoder import AesEncryptEncoder, AesDecryptEncoder
from kitty.model.low_level import BitField, RandomBytes
from common import BaseTestCase, metaTest, get_test_logger
from kitty.core import KittyException


class BitFieldMultiByteEncoderTests(BaseTestCase):

    def setUp(self, cls=None):
        super(BitFieldMultiByteEncoderTests, self).setUp(cls)

    def _multibyte_len(self, num):
        num_bits = len(bin(num)) - 2
        num_bytes = num_bits / 7
        if num_bits % 7 != 0:
            num_bytes += 1
        return num_bytes*8

    def _test(self, bitfield):
        expected_len = self._multibyte_len(bitfield._default_value)
        # bitfield.mutate()
        rendered = bitfield.render()
        self.assertEquals(expected_len, len(rendered))

    def test_unsigned_length_8(self):
        bitfield = BitField(
            0xaa,
            length=8,
            signed=False,
            max_value=255,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def test_unsigned_length_16(self):
        bitfield = BitField(
            1234,
            length=16,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def test_unsigned_length_32(self):
        bitfield = BitField(
            1234,
            length=32,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def test_unsigned_length_64(self):
        bitfield = BitField(
            78945,
            length=64,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def test_unsigned_length_11(self):
        bitfield = BitField(
            14,
            length=11,
            signed=False,
            encoder=BitFieldMultiByteEncoder()
        )
        self._test(bitfield)

    def test_BitFieldMultiByteEncoder_signed__unsupported(self):
        with self.assertRaises(KittyException):
            BitField(
                -12,
                length=8,
                signed=True,
                max_value=127,
                encoder=BitFieldMultiByteEncoder()
            )


class CryptorEncoderTestCase(BaseTestCase):

    __meta__ = True

    def setUp(self):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        self.key = '\x01' * 16
        self.iv = '\x02' * 16
        self.mode = AES.MODE_CBC
        self.key_size = 16
        self.key_provider = None

    def get_default_field(self, clear=True):
        encoder = ENC_STR_DEFAULT if clear else self.get_encoder()
        return RandomBytes('\x01' * 16, 16, 16, encoder=encoder)

    @metaTest
    def test_vanilla_base(self):
        self.logger.debug('get clear field')
        clear_field = self.get_default_field(True)
        self.logger.debug('get encoded field')
        encoded_field = self.get_default_field(False)
        self.logger.debug('get clear mutations')
        clear_mutations = [m.bytes for m in self.get_all_mutations(clear_field)]
        self.logger.debug('get encoded mutations')
        encoded_mutations = [m.bytes for m in self.get_all_mutations(encoded_field)]
        self.logger.debug('encoded clear mutations')
        expected_mutations = [self.encode(m) for m in clear_mutations]
        self.assertListEqual(encoded_mutations, expected_mutations)

    @metaTest
    def test_vanilla_CBC(self):
        self.mode = AES.MODE_CBC
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_ECB(self):
        self.mode = AES.MODE_ECB
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_128(self):
        self.key_size = 16
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_192(self):
        self.key_size = 24
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_256(self):
        self.key_size = 32
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_iv_default_to_zeros(self):
        self.iv = None
        self.test_vanilla_base()

    def _test_key_provider_base(self, size):
        self.i = 0

        def provider(key_size):
            self.i += 1
            self.logger.debug('provider called. i=%#x' % self.i)
            return chr(self.i % 256) * key_size

        self.key_size = size
        self.key = None
        self.key_provider = provider

        clear_field = self.get_default_field(True)
        encoded_field = self.get_default_field(False)
        clear_mutations = [m.bytes for m in self.get_all_mutations(clear_field)]
        self.i = 0
        encoded_mutations = [m.bytes for m in self.get_all_mutations(encoded_field)]
        self.assertEqual(len(clear_mutations), len(encoded_mutations))
        self.i = 0
        expected_mutations = [self.encode(m) for m in clear_mutations]
        self.assertEqual(encoded_mutations, expected_mutations)

    @metaTest
    def test_key_provider_128(self):
        self._test_key_provider_base(16)

    @metaTest
    def test_key_provider_192(self):
        self._test_key_provider_base(24)

    @metaTest
    def test_key_provider_256(self):
        self._test_key_provider_base(32)

    def _test_exception(self):
        with self.assertRaises(KittyException):
            self.get_default_field(False)

    @metaTest
    def test_exception_no_key_no_provider(self):
        self.key = '\x00' * 16
        self.key_provider = lambda x: '\x00' * 16
        self._test_exception()

    @metaTest
    def test_exception_key_and_provider(self):
        self.key = None
        self.key_provider = None
        self._test_exception()

    @metaTest
    def test_exception_bad_key_size_15(self):
        self.key_size = 15
        self._test_exception()

    @metaTest
    def test_exception_bad_key_size_20(self):
        self.key_size = 20
        self._test_exception()


class AesEncryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        super(AesEncryptEncoderTestCase, self).setUp()
        self.padder = None

    def get_encoder(self):
        return AesEncryptEncoder(
            key=self.key,
            iv=self.iv,
            mode=self.mode,
            key_size=self.key_size,
            key_provider=self.key_provider,
            padder=self.padder
        )

    def encode(self, data):
        key = self.key
        if self.key_provider:
            key = self.key_provider(self.key_size)
        iv = self.iv if self.iv else ('\x00' * 16)
        aes = AES.new(key=key, IV=iv, mode=self.mode)
        if self.padder:
            data = self.padder(data, 16)
        elif len(data) % 16:
            data += '\x00' * (16 - ((data) % 16))
        return aes.encrypt(data)

    def test_padder(self):
        def padder(data, block_size):
            if len(data) % block_size:
                data += '\x11' * (block_size - (len(data) % block_size))
            return data
        self.padder = padder

        def unaligned_default_field(clear=True):
            encoder = ENC_STR_DEFAULT if clear else self.get_encoder()
            return RandomBytes('\x01' * 16, 10, 18, encoder=encoder)

        self.get_default_field = unaligned_default_field
        self.test_vanilla_base()


class AesDecryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def get_encoder(self):
        return AesDecryptEncoder(
            key=self.key,
            iv=self.iv,
            mode=self.mode,
            key_size=self.key_size,
            key_provider=self.key_provider,
        )

    def encode(self, data):
        key = self.key
        if self.key_provider:
            key = self.key_provider(self.key_size)
        iv = self.iv if self.iv else ('\x00' * 16)
        aes = AES.new(key=key, IV=iv, mode=self.mode)
        return aes.decrypt(data)
