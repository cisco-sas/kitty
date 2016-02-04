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
from Crypto.Cipher import AES, DES, DES3
from kitty.model.low_level.encoder import BitFieldMultiByteEncoder
from kitty.model.low_level.encoder import ENC_STR_DEFAULT
from kitty.model.low_level.encoder import AesEncryptEncoder, AesDecryptEncoder
from kitty.model.low_level.encoder import AesCbcEncryptEncoder, AesEcbEncryptEncoder
from kitty.model.low_level.encoder import AesCbcDecryptEncoder, AesEcbDecryptEncoder
from kitty.model.low_level.encoder import DesEncryptEncoder, DesDecryptEncoder
from kitty.model.low_level.encoder import Des3EncryptEncoder, Des3DecryptEncoder
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


class CryptArgs(object):

    def __init__(self, key, iv, block_size, key_sizes, mode, key_provider):
        self.key = key
        self.iv = iv
        self.block_size = block_size
        self.key_sizes = key_sizes
        self.mode = mode
        self.key_provider = key_provider


class CryptorEncoderTestCase(BaseTestCase):

    __meta__ = True

    def setUp(self, crypt=None):
        self.logger = get_test_logger()
        self.logger.debug('TESTING METHOD: %s', self._testMethodName)
        if crypt is not None:
            self.crypto = crypt
            self.crypto.key_size = self.crypto.key_sizes[0]

    def get_default_field_with_encoder(self, encoder):
        return RandomBytes('\x01' * self.crypto.block_size, self.crypto.block_size, self.crypto.block_size, encoder=encoder)

    def get_default_field(self, clear=True):
        encoder = ENC_STR_DEFAULT if clear else self.get_encoder()
        return self.get_default_field_with_encoder(encoder)

    def dummy_provider(self, key_size):
        self.i += 1
        self.logger.debug('provider called. i=%#x' % self.i)
        return chr(self.i % 256) * key_size

    @metaTest
    def test_vanilla_base(self):
        clear_field = self.get_default_field(True)
        encoded_field = self.get_default_field(False)
        clear_mutations = [m.bytes for m in self.get_all_mutations(clear_field)]
        encoded_mutations = [m.bytes for m in self.get_all_mutations(encoded_field)]
        expected_mutations = [self.encode(m) for m in clear_mutations]
        self.assertListEqual(encoded_mutations, expected_mutations)

    @metaTest
    def test_vanilla_CBC(self):
        self.crypto.mode = AES.MODE_CBC
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_ECB(self):
        self.crypto.mode = AES.MODE_ECB
        self.test_vanilla_base()

    @metaTest
    def test_vanilla_128(self):
        self.crypto.key_size = 16
        self.test_vanilla_base()

    @metaTest
    def test_different_key_sizes(self):
        for size in self.crypto.key_sizes:
            self.logger.info('testing key size %#x' % size)
            self.crypto.key_size = size
            self.crypto.key = ''.join(chr(x) for x in range(size))
            self.test_vanilla_base()

    @metaTest
    def test_vanilla_iv_default_to_zeros(self):
        self.crypto.iv = None
        self.test_vanilla_base()

    def _test_key_provider_base(self, size):
        self.i = 0

        self.crypto.key_size = size
        self.crypto.key = None
        self.crypto.key_provider = self.dummy_provider

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
    def test_key_provider(self):
        for key_size in self.crypto.key_sizes:
            self.logger.info('Testing key provider for key size %#x' % key_size)
            self._test_key_provider_base(key_size)

    def _test_exception(self):
        with self.assertRaises(KittyException):
            self.get_default_field(False)

    @metaTest
    def test_exception_key_and_provider(self):
        self.crypto.key = '\x00' * self.crypto.key_size
        self.crypto.key_provider = lambda x: '\x00' * 16
        self._test_exception()

    @metaTest
    def test_exception_no_key_no_provider(self):
        self.crypto.key = None
        self.crypto.key_provider = None
        self._test_exception()

    @metaTest
    def test_exception_bad_key_size_15(self):
        self.crypto.key_size = 15
        self.crypto.key_provider = self.dummy_provider
        self._test_exception()

    @metaTest
    def test_exception_bad_key_size_20(self):
        self.crypto.key_size = 20
        self.crypto.key_provider = self.dummy_provider
        self._test_exception()

    def _test_generators_base(self, encoder):
        clear_field = self.get_default_field(True)
        encoded_field = self.get_default_field_with_encoder(encoder)
        clear_mutations = [m.bytes for m in self.get_all_mutations(clear_field)]
        encoded_mutations = [m.bytes for m in self.get_all_mutations(encoded_field)]
        expected_mutations = [self.encode(m) for m in clear_mutations]
        self.assertListEqual(encoded_mutations, expected_mutations)


class AesEncryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        crypt = CryptArgs('\x01' * 16, '\x00' * 16, 16, [16, 24, 32], AES.MODE_CBC, None)
        super(AesEncryptEncoderTestCase, self).setUp(crypt)
        self.crypto.padder = None

    def get_encoder(self):
        return AesEncryptEncoder(
            key=self.crypto.key,
            iv=self.crypto.iv,
            mode=self.crypto.mode,
            key_size=self.crypto.key_size,
            key_provider=self.crypto.key_provider,
            padder=self.crypto.padder
        )

    def encode(self, data):
        key = self.crypto.key
        if self.crypto.key_provider:
            key = self.crypto.key_provider(self.crypto.key_size)
        iv = self.crypto.iv if self.crypto.iv else ('\x00' * 16)
        aes = AES.new(key=key, IV=iv, mode=self.crypto.mode)
        if self.crypto.padder:
            data = self.crypto.padder(data, self.crypto.block_size)
        elif len(data) % self.crypto.block_size:
            data += '\x00' * (self.crypto.block_size - (len(data) % self.crypto.block_size))
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

    def test_AesCbcEncryptEncoder(self):
        '''
        AesCbcEncryptEncoder(key=None, iv=None, key_size=16, key_provider=None, padder=None)
        '''
        self.crypto.mode = AES.MODE_CBC
        self._test_generators_base(
            AesCbcEncryptEncoder(
                key=self.crypto.key,
                iv=self.crypto.iv,
                key_size=self.crypto.key_size,
                key_provider=self.crypto.key_provider,
                padder=self.crypto.padder
            ))

    def test_AesEcbEncryptEncoder(self):
        '''
        AesEcbEncryptEncoder(key=None, iv=None, key_size=16, key_provider=None, padder=None)
        '''
        self.crypto.mode = AES.MODE_ECB
        self._test_generators_base(
            AesEcbEncryptEncoder(
                key=self.crypto.key,
                iv=self.crypto.iv,
                key_size=self.crypto.key_size,
                key_provider=self.crypto.key_provider,
                padder=self.crypto.padder
            ))


class AesDecryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        crypto = CryptArgs('\x01' * 16, '\x00' * 16, 16, [16, 24, 32], AES.MODE_CBC, None)
        super(AesDecryptEncoderTestCase, self).setUp(crypto)

    def get_encoder(self):
        return AesDecryptEncoder(
            key=self.crypto.key,
            iv=self.crypto.iv,
            mode=self.crypto.mode,
            key_size=self.crypto.key_size,
            key_provider=self.crypto.key_provider,
        )

    def encode(self, data):
        key = self.crypto.key
        if self.crypto.key_provider:
            key = self.crypto.key_provider(self.crypto.key_size)
        iv = self.crypto.iv if self.crypto.iv else ('\x00' * self.crypto.block_size)
        aes = AES.new(key=key, IV=iv, mode=self.crypto.mode)
        decrypted = aes.decrypt(data)
        return decrypted

    def test_AesCbcDecryptEncoder(self):
        '''
        AesCbcDecryptEncoder(key=None, iv=None, key_size=16, key_provider=None)
        '''
        self.crypto.mode = AES.MODE_CBC
        self._test_generators_base(
            AesCbcDecryptEncoder(
                key=self.crypto.key,
                iv=self.crypto.iv,
                key_size=self.crypto.key_size,
                key_provider=self.crypto.key_provider,
            ))

    def test_AesEcbDecryptEncoder(self):
        '''
        AesEcbDecryptEncoder(key=None, iv=None, key_size=16, key_provider=None)
        '''
        self.crypto.mode = AES.MODE_ECB
        self._test_generators_base(
            AesEcbDecryptEncoder(
                key=self.crypto.key,
                iv=self.crypto.iv,
                key_size=self.crypto.key_size,
                key_provider=self.crypto.key_provider,
            ))


class DesEncryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        crypt = CryptArgs('\x01' * 8, '\x00' * 8, 8, [8], DES.MODE_CBC, None)
        super(DesEncryptEncoderTestCase, self).setUp(crypt)
        self.crypto.padder = None

    def get_encoder(self):
        return DesEncryptEncoder(
            key=self.crypto.key,
            iv=self.crypto.iv,
            mode=self.crypto.mode,
            key_size=self.crypto.key_size,
            key_provider=self.crypto.key_provider,
            padder=self.crypto.padder
        )

    def encode(self, data):
        key = self.crypto.key
        if self.crypto.key_provider:
            key = self.crypto.key_provider(self.crypto.key_size)
        iv = self.crypto.iv if self.crypto.iv else ('\x00' * 8)
        des = DES.new(key=key, IV=iv, mode=self.crypto.mode)
        if self.crypto.padder:
            data = self.crypto.padder(data, self.crypto.block_size)
        elif len(data) % self.crypto.block_size:
            data += '\x00' * (self.crypto.block_size - (len(data) % self.crypto.block_size))
        return des.encrypt(data)

    def test_padder(self):
        def padder(data, block_size):
            if len(data) % block_size:
                data += '\x11' * (block_size - (len(data) % block_size))
            return data
        self.padder = padder

        def unaligned_default_field(clear=True):
            encoder = ENC_STR_DEFAULT if clear else self.get_encoder()
            return RandomBytes('\x01' * 10, 10, 18, encoder=encoder)

        self.get_default_field = unaligned_default_field
        self.test_vanilla_base()


class DesDecryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        crypt = CryptArgs('\x01' * 8, '\x00' * 8, 8, [8], DES.MODE_CBC, None)
        super(DesDecryptEncoderTestCase, self).setUp(crypt)

    def get_encoder(self):
        return DesDecryptEncoder(
            key=self.crypto.key,
            iv=self.crypto.iv,
            mode=self.crypto.mode,
            key_size=self.crypto.key_size,
            key_provider=self.crypto.key_provider,
        )

    def encode(self, data):
        key = self.crypto.key
        if self.crypto.key_provider:
            key = self.crypto.key_provider(self.crypto.key_size)
        iv = self.crypto.iv if self.crypto.iv else ('\x00' * self.crypto.block_size)
        des = DES.new(key=key, IV=iv, mode=self.crypto.mode)
        decrypted = des.decrypt(data)
        return decrypted


class Des3EncryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        crypt = CryptArgs('\x01' * 16, '\x00' * 8, 8, [16, 24], DES3.MODE_CBC, None)
        super(Des3EncryptEncoderTestCase, self).setUp(crypt)
        self.crypto.padder = None

    def get_encoder(self):
        return Des3EncryptEncoder(
            key=self.crypto.key,
            iv=self.crypto.iv,
            mode=self.crypto.mode,
            key_size=self.crypto.key_size,
            key_provider=self.crypto.key_provider,
            padder=self.crypto.padder
        )

    def encode(self, data):
        key = self.crypto.key
        if self.crypto.key_provider:
            key = self.crypto.key_provider(self.crypto.key_size)
        iv = self.crypto.iv if self.crypto.iv else ('\x00' * 8)
        des3 = DES3.new(key=key, IV=iv, mode=self.crypto.mode)
        if self.crypto.padder:
            data = self.crypto.padder(data, self.crypto.block_size)
        elif len(data) % self.crypto.block_size:
            data += '\x00' * (self.crypto.block_size - (len(data) % self.crypto.block_size))
        return des3.encrypt(data)

    def test_padder(self):
        def padder(data, block_size):
            if len(data) % block_size:
                data += '\x11' * (block_size - (len(data) % block_size))
            return data
        self.padder = padder

        def unaligned_default_field(clear=True):
            encoder = ENC_STR_DEFAULT if clear else self.get_encoder()
            return RandomBytes('\x01' * 10, 10, 18, encoder=encoder)

        self.get_default_field = unaligned_default_field
        self.test_vanilla_base()


class Des3DecryptEncoderTestCase(CryptorEncoderTestCase):

    __meta__ = False

    def setUp(self):
        crypt = CryptArgs('\x01' * 16, '\x00' * 8, 8, [16, 24], DES3.MODE_CBC, None)
        super(Des3DecryptEncoderTestCase, self).setUp(crypt)

    def get_encoder(self):
        return Des3DecryptEncoder(
            key=self.crypto.key,
            iv=self.crypto.iv,
            mode=self.crypto.mode,
            key_size=self.crypto.key_size,
            key_provider=self.crypto.key_provider,
        )

    def encode(self, data):
        key = self.crypto.key
        if self.crypto.key_provider:
            key = self.crypto.key_provider(self.crypto.key_size)
        iv = self.crypto.iv if self.crypto.iv else ('\x00' * self.crypto.block_size)
        des3 = DES3.new(key=key, IV=iv, mode=self.crypto.mode)
        decrypted = des3.decrypt(data)
        return decrypted
