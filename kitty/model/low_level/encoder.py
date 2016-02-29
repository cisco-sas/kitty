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

        # split to septets
        if value:
            bytes_arr = []
            while value:
                bytes_arr.append((value & 0x7f) | 0x80)
                value >>= 7
        else:
            bytes_arr = [0]

        # reverse if big endian endian
        if self._mode == 'be':
            bytes_arr.reverse()

        # remove msb from last byte
        bytes_arr[-1] = bytes_arr[-1] & 0x7f

        multi_bytes = ''.join(chr(x) for x in bytes_arr)
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
            value += Bits(bin='0' * (8-remainder))
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
