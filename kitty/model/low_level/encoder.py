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
Encoders are used for encoding fields and containers.
The encoders are passed as an argument to the fields/container, during the field rendering,
the encoder's `encode` method is called.

There are three families of encoders:

:Bits Encoders: Used to encode fields/containers that their value is of type *Bits* (Container, ForEach etc.)

:String Encoders: Used to encode fields that their value is of type *str* (String, Delimiter, RandomBytes etc.)

:BitField Encoders:
    Used to encode fields that inherit from BitField or contain BitField (UInt8, Size, Checksum etc.)
    Those encoders are also refferred to as Int Encoders.
'''
from bitstring import Bits, BitArray
from Crypto.Cipher import AES, DES, DES3
from kitty.core import kassert, KittyException


# ################### String Encoders ####################

class StrEncoder(object):
    '''
    Base encoder class for str values
    The String encoders *encode* function receives a *str* object as an argument and returns an encoded *Bits* object.

    +----------------------+------------------------------------+---------------------------+
    | Singleton Name       | Encoding                           | Class                     |
    +======================+====================================+===========================+
    | ENC_STR_UTF8         | Encode the str in UTF-8            | StrEncodeEncoder          |
    +----------------------+------------------------------------+                           |
    | ENC_STR_HEX          | Encode the str in hex              |                           |
    +----------------------+------------------------------------+                           |
    | ENC_STR_BASE64       | Encode the str in base64           |                           |
    +----------------------+------------------------------------+---------------------------+
    | ENC_STR_BASE64_NO_NL | Encode the str in base64 but       | StrBase64NoNewLineEncoder |
    |                      | remove the new line from the end   |                           |
    +----------------------+------------------------------------+---------------------------+
    | ENC_STR_DEFAULT      | Do nothing, just convert the str   | StrEncoder                |
    |                      | to Bits object                     |                           |
    +----------------------+------------------------------------+---------------------------+
    '''

    def encode(self, value):
        '''
        :type value: ``str``
        :param value: value to encode
        '''
        kassert.is_of_types(value, str)
        return Bits(bytes=value)


class StrFuncEncoder(StrEncoder):
    '''
    Encode string using a given function
    '''
    def __init__(self, func):
        '''
        :param func: encoder function(str)->str
        '''
        super(StrFuncEncoder, self).__init__()
        self._func = func

    def encode(self, value):
        kassert.is_of_types(value, str)
        encoded = self._func(value)
        return Bits(bytes=encoded)


class StrEncodeEncoder(StrEncoder):
    '''
    Encode the string using str.encode function
    '''
    def __init__(self, encoding):
        '''
        :type encoding: ``str``
        :param encoding: encoding to be used, should be a valid argument for str.encode
        '''
        super(StrEncodeEncoder, self).__init__()
        self._encoding = encoding

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, str)
        try:
            encoded = value.encode(self._encoding)
        except UnicodeError:
            # TODO: make it better
            try:
                encoded = ''.join(unichr(ord(x)) for x in value).encode(self._encoding)
            except UnicodeError:
                encoded = value

        return Bits(bytes=encoded)


class StrBase64NoNewLineEncoder(StrEncoder):
    '''
    Encode the string as base64, but without the new line at the end
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, str)
        encoded = value.encode('base64')
        if encoded:
            encoded = encoded[:-1]
        return Bits(bytes=encoded)


class StrNullTerminatedEncoder(StrEncoder):
    '''
    Encode the string as c-string, with null at the end
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, str)
        encoded = value + '\x00'
        return Bits(bytes=encoded)


def _pad_zeros(data, block_size):
    '''
    pad a string to multiples of block_size

    :param data: data to pad
    :param block_size: size of block
    :return: padded data
    '''
    pad = ''
    remainder = len(data) % block_size
    if remainder:
        pad = '\x00' * (block_size - remainder)
    return data + pad


class BlockCipherEncoder(StrEncoder):
    '''
    Generic block cipher encoder.
    '''
    _key_sizes_ = None
    _iv_size_ = None
    _block_size_ = None
    _default_key_size_ = None
    _default_mode_ = None

    def __init__(self, key=None, iv=None, mode=None, key_size=None, key_provider=None, padder=None):
        '''
        All fields default to None.
        :type key: str
        :param key: encryption key, must be 8 bytes
        :param iv: iv, must be 8 bytes long, if None - use zeros
        :param mode: encrytion mode
        :param key_size: size of key, should be provided only when using key provider
        :type key_provider: function(key_size) -> str
        :param key_provider: function that returns key
        :type padder: function(str, block_size) -> str
        :param padder: function that pads the data, if None - will pad with zeros
        '''
        self.key = key
        self.iv = iv
        self.mode = mode
        self.key_size = key_size
        self.key_provider = key_provider
        self.padder = padder
        self._check_args()

    def _check_args(self):
        '''
        This is a massive check. argh...
        '''
        if self.key:
            if len(self.key) not in self._key_sizes_:
                raise KittyException('provided key size (%d) not in %s' % (len(self.key), self._key_sizes_))
            if self.key_provider:
                raise KittyException('You should not provide both key and key_provider.')
        elif self.key_provider:
            if not callable(self.key_provider):
                raise KittyException('key_provider must be callable')
            if not self.key_size:
                if self._default_key_size_:
                    self.key_size = self._default_key_size_
                else:
                    raise KittyException('key_size should be specified when using key_provider')
            if self.key_size not in self._key_sizes_:
                raise KittyException('key size (%d) not a valid one (use %s)' % (self.key_size, self._key_sizes_))
        else:
            raise KittyException('You need to provide either key or key_provider')
        if not self.iv:
            self.iv = '\x00' * self._iv_size_
        if len(self.iv) != self._iv_size_:
            raise KittyException('Invalid iv size: %#x. Expected: %#x')
        if not self.padder:
            self.padder = self._zero_padder
        if self.mode is None:
            self.mode = self._default_mode_

    def _zero_padder(self, data, blocksize):
        remainder = len(data) % self._block_size_
        if remainder:
            data += '\x00' * (self._block_size_ - remainder)
        return data


class BlockEncryptEncoder(BlockCipherEncoder):
    '''
    Generic block cipher encryption encoder.
    '''

    def encode(self, data):
        self.current_key = self.key
        if self.key_provider:
            self.current_key = self.key_provider(self.key_size)
        cipher = self._cipher_class_.new(key=self.current_key, mode=self.mode, IV=self.iv)
        encrypted = cipher.encrypt(self.padder(data, 16))
        return Bits(bytes=encrypted)


class AesEncryptEncoder(BlockEncryptEncoder):
    '''
    AES encryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''
    _key_sizes_ = [16, 24, 32]
    _iv_size_ = 16
    _block_size_ = 16
    _default_key_size_ = 16
    _default_mode_ = AES.MODE_CBC
    _cipher_class_ = AES


class DesEncryptEncoder(BlockEncryptEncoder):
    '''
    DES encryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''
    _key_sizes_ = [8]
    _iv_size_ = 8
    _block_size_ = 8
    _default_key_size_ = 8
    _default_mode_ = DES.MODE_CBC
    _cipher_class_ = DES


class Des3EncryptEncoder(BlockEncryptEncoder):
    '''
    3DES encryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''
    _key_sizes_ = [16, 24]
    _iv_size_ = 8
    _block_size_ = 8
    _default_key_size_ = 8
    _default_mode_ = DES3.MODE_CBC
    _cipher_class_ = DES3


class BlockDecryptEncoder(BlockCipherEncoder):
    '''
    Generic block cipher decryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''

    def encode(self, data):
        if len(data) % self._block_size_:
            raise KittyException('data must be %d-bytse aligned' % self._block_size_)
        self.current_key = self.key
        if self.key_provider:
            self.current_key = self.key_provider(self.key_size)
        cipher = self._cipher_class_.new(key=self.current_key, mode=self.mode, IV=self.iv)
        decrypted = cipher.decrypt(data)
        # print 'data', data.encode('hex')
        # print 'decrypted', decrypted.encode('hex')
        # print 'current key', self.current_key.encode('hex')
        # print 'IV', self.iv.encode('hex')
        # print 'mode', self.mode
        return Bits(bytes=decrypted)


class AesDecryptEncoder(BlockDecryptEncoder):
    '''
    AES decryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''
    _key_sizes_ = [16, 24, 32]
    _iv_size_ = 16
    _block_size_ = 16
    _default_key_size_ = 16
    _default_mode_ = AES.MODE_CBC
    _cipher_class_ = AES


class DesDecryptEncoder(BlockDecryptEncoder):
    '''
    DES decryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''
    _key_sizes_ = [8]
    _iv_size_ = 8
    _block_size_ = 8
    _default_key_size_ = 8
    _default_mode_ = DES.MODE_CBC
    _cipher_class_ = DES


class Des3DecryptEncoder(BlockDecryptEncoder):
    '''
    3DES decryption encoder.
    See :class:`~kitty.model.low_level.encoders.BlockCipherEncoder` for parameters.
    '''
    _key_sizes_ = [16, 24]
    _iv_size_ = 8
    _block_size_ = 8
    _default_key_size_ = 8
    _default_mode_ = DES3.MODE_CBC
    _cipher_class_ = DES3


def AesCbcEncryptEncoder(key=None, iv=None, key_size=16, key_provider=None, padder=None):
    '''
    AES CBC Encrypt encoder.
    See :class:`~kitty.model.low_level.encoder.AesEncryptEncoder` for parameter description.
    '''
    return AesEncryptEncoder(key, iv, AES.MODE_CBC, key_size, key_provider, padder)


def AesEcbEncryptEncoder(key=None, iv=None, key_size=16, key_provider=None, padder=None):
    '''
    AES ECB Encrypt encoder.
    See :class:`~kitty.model.low_level.encoder.AesEncryptEncoder` for parameter description.
    '''
    return AesEncryptEncoder(key, iv, AES.MODE_ECB, key_size, key_provider, padder)


def AesCbcDecryptEncoder(key=None, iv=None, key_size=16, key_provider=None):
    '''
    AES CBC Decrypt encoder.
    See :class:`~kitty.model.low_level.encoder.AesDecryptEncoder` for parameter description.
    '''
    return AesDecryptEncoder(key, iv, AES.MODE_CBC, key_size, key_provider)


def AesEcbDecryptEncoder(key=None, iv=None, key_size=16, key_provider=None):
    '''
    AES ECB Decrypt encoder.
    See :class:`~kitty.model.low_level.encoder.AesDecryptEncoder` for parameter description.
    '''
    return AesDecryptEncoder(key, iv, AES.MODE_ECB, key_size, key_provider)


ENC_STR_BASE64 = StrEncodeEncoder('base64')
ENC_STR_BASE64_NO_NL = StrBase64NoNewLineEncoder()
ENC_STR_UTF8 = StrEncodeEncoder('utf-8')
ENC_STR_HEX = StrEncodeEncoder('hex')
ENC_STR_NULL_TERM = StrNullTerminatedEncoder()
ENC_STR_DEFAULT = StrEncoder()


# ################### BitField (int) Encoders ####################

class BitFieldEncoder(object):
    '''
    Base encoder class for BitField values

    +-------------------+---------------------------------------+-----------------------+
    | Singleton Name    | Encoding                              | Class                 |
    +===================+=======================================+=======================+
    | ENC_INT_BIN       | Encode as binary bits                 | BitFieldBinEncoder    |
    +-------------------+---------------------------------------+-----------------------+
    | ENC_INT_LE        | Encode as a little endian binary bits | BitFieldBinEncoder    |
    +-------------------+---------------------------------------+                       |
    | ENC_INT_BE        | Encode as a big endian binary bits    |                       |
    +-------------------+---------------------------------------+-----------------------+
    | ENC_INT_DEC       | Encode as a decimal value             | BitFieldAsciiEncoder  |
    +-------------------+---------------------------------------+                       |
    | ENC_INT_HEX       | Encode as a hex value                 |                       |
    +-------------------+---------------------------------------+                       |
    | ENC_INT_HEX_UPPER | Encode as an upper case hex value     |                       |
    +-------------------+---------------------------------------+-----------------------+
    | ENC_INT_DEFAULT   | Same as ENC_INT_BIN                   |                       |
    +-------------------+---------------------------------------+-----------------------+
    '''

    def encode(self, value, length, signed):
        '''
        :type value: ``int``
        :param value: value to encode
        :type length: ``int``
        :param length: length of value in bits
        :type signed: ``boolean``
        :param signed: is value signed
        '''
        raise NotImplementedError('should be implemented in sub classes')


class BitFieldBinEncoder(BitFieldEncoder):
    '''
    Encode int as binary
    '''

    def __init__(self, mode):
        '''
        :type mode: str
        :param mode: mode of binary encoding. 'le' for little endian, 'be' for big endian, '' for non-byte aligned
        '''
        kassert.is_in(mode, ['', 'be', 'le'])
        super(BitFieldBinEncoder, self).__init__()
        self._mode = mode

    def encode(self, value, length, signed):
        '''
        :param value: value to encode
        :param length: length of value in bits
        :param signed: is value signed
        '''
        if (length % 8 != 0) and self._mode:
            raise Exception('cannot use endianess for non bytes aligned int')
        pre = '' if signed else 'u'
        fmt = '%sint%s:%d=%d' % (pre, self._mode, length, value)
        return Bits(fmt)


class BitFieldAsciiEncoder(BitFieldEncoder):
    '''
    Encode int as ascii
    '''

    formats = ['%d', '%x', '%X', '%#x', '%#X']

    def __init__(self, fmt):
        '''
        :param fmt: format for encoding (from BitFieldAsciiEncoder.formats)
        '''
        kassert.is_in(fmt, BitFieldAsciiEncoder.formats)
        self._fmt = fmt

    def encode(self, value, length, signed):
        return Bits(bytes=self._fmt % value)


class BitFieldMultiByteEncoder(BitFieldEncoder):
    '''
    Encode int as multi-byte (used in WBXML format)
    '''

    def __init__(self, mode='be'):
        '''
        :type mode: str
        :param mode: mode of binary encoding. 'le' for little endian, 'be' for big endian, '' for non-byte aligned
        '''
        kassert.is_in(mode, ['be', 'le'])
        super(BitFieldMultiByteEncoder, self).__init__()
        self._mode = mode

    def encode(self, value, length, signed):
        '''
        :param value: value to encode
        :param length: length of value in bits
        :param signed: is value signed
        '''
        if signed:
            raise KittyException('Signed MultiBytes not supported yet, sorry')
        single_byte = chr(value & 0x7f)
        multi_bytes = single_byte
        value = value >> 7
        while value:
            single_byte = chr(0x80 | (value & 0x7f))
            multi_bytes = single_byte + multi_bytes
            value = value >> 7
        return Bits(bytes=multi_bytes)


ENC_INT_BIN = BitFieldBinEncoder('')
ENC_INT_LE = BitFieldBinEncoder('le')
ENC_INT_BE = BitFieldBinEncoder('be')

ENC_INT_DEC = BitFieldAsciiEncoder('%d')
ENC_INT_HEX = BitFieldAsciiEncoder('%x')
ENC_INT_HEX_UPPER = BitFieldAsciiEncoder('%X')
ENC_INT_DEFAULT = ENC_INT_BIN

ENC_INT_MULTIBYTE_BE = BitFieldMultiByteEncoder('be')

# ################### Bits Encoders ####################


class BitsEncoder(object):
    '''
    Base encoder class for Bits values

    The Bits encoders *encode* function receives a *Bits* object as an argument and returns an encoded *Bits* object.

    +-----------------------+----------------------------------------+------------------------+
    | Singleton Name        | Encoding                               | Class                  |
    +=======================+========================================+========================+
    | ENC_BITS_NONE         | None, returns the same value received  | BitsEncoder            |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_BYTE_ALIGNED | Appends bits to the received object to | ByteAlignedBitsEncoder |
    |                       | make it byte aligned                   |                        |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_REVERSE      | Reverse the order of bits              | ReverseBitsEncoder     |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_BASE64       | Encode a Byte aligned bits in base64   | StrEncoderWrapper      |
    +-----------------------+----------------------------------------+                        |
    | ENC_BITS_BASE64_NO_NL | Encode a Byte aligned bits in base64,  |                        |
    |                       | but removes the new line from the end  |                        |
    +-----------------------+----------------------------------------+                        |
    | ENC_BITS_UTF8         | Encode a Byte aligned bits in UTF-8    |                        |
    +-----------------------+----------------------------------------+                        |
    | ENC_BITS_HEX          | Encode a Byte aligned bits in hex      |                        |
    +-----------------------+----------------------------------------+------------------------+
    | ENC_BITS_DEFAULT      | Same as ENC_BITS_NONE                  |                        |
    +-----------------------+----------------------------------------+------------------------+
    '''

    def encode(self, value):
        '''
        :type value: Bits
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        return value


class ByteAlignedBitsEncoder(BitsEncoder):
    '''
    Stuff bits for byte alignment
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        remainder = len(value) % 8
        if remainder:
            value += Bits(remainder)
        return value


class ReverseBitsEncoder(BitsEncoder):
    '''
    Reverse the order of bits
    '''

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        result = BitArray(value)
        result.reverse()
        return result


class StrEncoderWrapper(ByteAlignedBitsEncoder):
    '''
    Encode the data using str.encode function
    '''
    def __init__(self, encoder):
        '''
        :type encoding: StrEncoder
        :param encoding: encoder to wrap
        '''
        super(StrEncoderWrapper, self).__init__()
        self._encoder = encoder

    def encode(self, value):
        '''
        :param value: value to encode
        '''
        kassert.is_of_types(value, Bits)
        if len(value) % 8 != 0:
            raise KittyException('this encoder cannot encode bits that are not byte aligned')
        return self._encoder.encode(value.bytes)


class BitsFuncEncoder(StrEncoder):
    '''
    Encode bits using a given function
    '''
    def __init__(self, func):
        '''
        :param func: encoder function(Bits)->Bits
        '''
        super(BitsFuncEncoder, self).__init__()
        self._func = func

    def encode(self, value):
        kassert.is_of_types(value, Bits)
        encoded = self._func(value)
        return encoded


ENC_BITS_NONE = BitsEncoder()
ENC_BITS_BYTE_ALIGNED = ByteAlignedBitsEncoder()
ENC_BITS_REVERSE = ReverseBitsEncoder()

ENC_BITS_BASE64 = StrEncoderWrapper(StrEncodeEncoder('base64'))
ENC_BITS_BASE64_NO_NL = StrEncoderWrapper(StrBase64NoNewLineEncoder())
ENC_BITS_UTF8 = StrEncoderWrapper(StrEncodeEncoder('utf-8'))
ENC_BITS_HEX = StrEncoderWrapper(StrEncodeEncoder('hex'))

ENC_BITS_DEFAULT = ENC_BITS_NONE
