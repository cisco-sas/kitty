'''
Tests for mutation based fields
'''

from common import BaseTestCase
from kitty.core import KittyException
from kitty.model.low_level.mutated_field import BitFlip, ByteFlip
from kitty.model.low_level.mutated_field import BitFlips, ByteFlips
from struct import pack


class BitFlipTests(BaseTestCase):

    def setUp(self):
        super(BitFlipTests, self).setUp(None)

    def _testBase(self, value, num_bits_to_flip, expected_mutations):
        len_in_bits = len(value) * 8
        uut = BitFlip(value=value, num_bits=num_bits_to_flip)
        self.assertEqual(uut.num_mutations(), len_in_bits - num_bits_to_flip + 1)
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertEqual(set(mutations), set(expected_mutations))

    def testFlipSingleBitOnSingleByte(self):
        expected_mutations = map(lambda i: chr(1 << i), range(8))
        self._testBase('\x00', 1, expected_mutations)

    def testFlipTwoBitsOnSingleByte(self):
        expected_mutations = map(lambda i: chr(3 << i), range(7))
        self._testBase('\x00', 2, expected_mutations)

    def testFlipAllBitsOnSingleByte(self):
        expected_mutations = ['\xff']
        self._testBase('\x00', 8, expected_mutations)

    def testFlipSingleBitOnTwoBytes(self):
        expected_mutations = map(lambda i: pack('>H', 1 << i), range(16))
        self._testBase('\x00\x00', 1, expected_mutations)

    def testFlipTwoBitsOnTwoBytes(self):
        expected_mutations = map(lambda i: pack('>H', 3 << i), range(15))
        self._testBase('\x00\x00', 2, expected_mutations)

    def testFlipTenBitsOnTwoBytes(self):
        expected_mutations = map(lambda i: pack('>H', 0x3ff << i), range(7))
        self._testBase('\x00\x00', 10, expected_mutations)

    def testFlipAllBitsOnTwoBytes(self):
        expected_mutations = map(lambda i: pack('>H', 0xffff << i), range(1))
        self._testBase('\x00\x00', 16, expected_mutations)

    def testFuzzableIsFalse(self):
        uut = BitFlip('\x00\x00',  num_bits=3, fuzzable=False)
        self.assertEqual(uut.num_mutations(), 0)
        self.assertEqual(self.get_all_mutations(uut), [])

    def testExceptionIfNumOfBitsIsBiggerThanValue(self):
        with self.assertRaises(KittyException):
            value = '\x00'
            max_len = len(value) * 8
            BitFlip(value=value, num_bits=max_len + 1)

    def testExceptionIfNumOfBitsIsNegative(self):
        with self.assertRaises(KittyException):
            value = '\x00'
            BitFlip(value=value, num_bits=-1)


class BitFlipsTests(BaseTestCase):

    def setUp(self):
        super(BitFlipsTests, self).setUp(None)

    def _generate_mutations(self, num_bytes, num_bits_itr):
        formats = {1: '>B', 2: '>H', 4: '>I'}
        if num_bytes not in formats:
            raise Exception('cannot generate mutations for %#x bytes' % num_bytes)
        fmt = formats[num_bytes]
        generated = []
        total_bits = num_bytes * 8
        for num_bits in num_bits_itr:
            mask = (1 << num_bits) - 1
            generated.extend(map(lambda x: pack(fmt, mask << x), range(total_bits - num_bits + 1)))
        return generated

    def _testBase(self, num_bytes, itr, uut=None):
        if uut is None:
            uut = BitFlips('\x00' * num_bytes, itr)
        expected_mutations = self._generate_mutations(num_bytes, itr)
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertGreaterEqual(len(mutations), len(expected_mutations))
        for em in expected_mutations:
            self.assertIn(em, mutations)

    def testSingleByteDefaultRangeIs1to5(self):
        uut = BitFlips('\x00')
        expected_mutations = self._generate_mutations(1, range(1, 5))
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertGreaterEqual(len(mutations), len(expected_mutations))
        for em in expected_mutations:
            self.assertIn(em, mutations)

    def testTwoBytesDefaultRangeIs1to5(self):
        uut = BitFlips('\x00\x00')
        expected_mutations = self._generate_mutations(2, range(1, 5))
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertGreaterEqual(len(mutations), len(expected_mutations))
        for em in expected_mutations:
            self.assertIn(em, mutations)

    def testSingleByteSingleRange(self):
        self._testBase(1, [1])

    def testSingleByteMaximumRange(self):
        self._testBase(1, range(1, 9))

    def testSingleByteArbitraryRange(self):
        self._testBase(1, [1, 4, 6, 3])

    def testMultipleBytesSingleRange(self):
        self._testBase(4, [1])

    def testMultipleBytesMaximumRange(self):
        self._testBase(4, range(1, 33))

    def testMultipleBytesArbitraryRange(self):
        self._testBase(4, [5, 19, 22, 27, 6])

    def testExceptionIfRangeOverflowsSingleByte(self):
        with self.assertRaises(KittyException):
            BitFlips('\x00', bits_range=[9])

    def testExceptionIfUnorderedRangeOverflowsSingleByte(self):
        with self.assertRaises(KittyException):
            BitFlips('\x00', bits_range=[2, 9, 1])

    def testExceptionIfRangeOverflowsMultipleBytes(self):
        with self.assertRaises(KittyException):
            BitFlips('\x00\x00\x00\x00', bits_range=[33])

    def testExceptionIfUnorderedRangeOverflowsMultipleBytes(self):
        with self.assertRaises(KittyException):
            BitFlips('\x00', bits_range=[12, 33, 7])


class ByteFlipTests(BaseTestCase):

    def setUp(self):
        super(ByteFlipTests, self).setUp(None)

    def _testFlipBytes(self, bytes_to_flip, value_len):
        value = '\x00' * value_len
        nf_count = value_len - bytes_to_flip
        expected_mutations = map(lambda i: '\x00' * (nf_count - i) + '\xff' * bytes_to_flip + '\x00' * (i), range(nf_count + 1))
        uut = ByteFlip(value=value, num_bytes=bytes_to_flip)
        self.assertEqual(uut.num_mutations(), value_len - bytes_to_flip + 1)
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertEqual(set(mutations), set(expected_mutations))

    def testFlipSingleByteOnSingleByte(self):
        self._testFlipBytes(1, 1)

    def testFlipSingleByteOnTwoBytes(self):
        self._testFlipBytes(1, 2)

    def testFlipTwoBytesOnMultipleBytes(self):
        self._testFlipBytes(2, 10)

    def testFlipFourBytesOnMultipleBytes(self):
        self._testFlipBytes(4, 10)

    def testFlipAllOnMultiple(self):
        self._testFlipBytes(10, 10)

    def testExceptionIfNumOfBytesIsBiggerThanValue(self):
        with self.assertRaises(KittyException):
            value = '\x00'
            max_len = len(value)
            ByteFlip(value=value, num_bytes=max_len + 1)

    def testExceptionIfNumOfBitsIsNegative(self):
        with self.assertRaises(KittyException):
            value = '\x00'
            ByteFlip(value=value, num_bytes=-1)

    def testFuzzableIsFalse(self):
        uut = ByteFlip('\x00\x00\x00\x00',  num_bytes=2, fuzzable=False)
        self.assertEqual(uut.num_mutations(), 0)
        self.assertEqual(self.get_all_mutations(uut), [])


class ByteFlipsTests(BaseTestCase):

    def setUp(self):
        super(ByteFlipsTests, self).setUp(None)

    def _generate_single(self, value_len, bytes_to_flip):
        nf_count = value_len - bytes_to_flip
        expected_mutations = map(lambda i: '\x00' * (nf_count - i) + '\xff' * bytes_to_flip + '\x00' * (i), range(nf_count + 1))
        return expected_mutations

    def _generate_mutations(self, value_len, num_bytes_itr):
        generated = []
        for num_bytes in num_bytes_itr:
            generated.extend(self._generate_single(value_len, num_bytes))
        return generated

    def _testBase(self, num_bytes, itr, uut=None):
        if uut is None:
            uut = ByteFlips('\x00' * num_bytes, itr)
        expected_mutations = self._generate_mutations(num_bytes, itr)
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertGreaterEqual(len(mutations), len(expected_mutations))
        for em in expected_mutations:
            self.assertIn(em, mutations)

    def testFourByteDefaultRangeIs124(self):
        uut = ByteFlips('\x00\x00\x00\x00')
        expected_mutations = self._generate_mutations(4, [1, 2, 4])
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertGreaterEqual(len(mutations), len(expected_mutations))
        for em in expected_mutations:
            self.assertIn(em, mutations)

    def testTenBytesDefaultRangeIs124(self):
        uut = ByteFlips('\x00' * 10)
        expected_mutations = self._generate_mutations(10, [1, 2, 4])
        mutations = map(lambda x: x.tobytes(), self.get_all_mutations(uut))
        self.assertGreaterEqual(len(mutations), len(expected_mutations))
        for em in expected_mutations:
            self.assertIn(em, mutations)

    def testSingleByteSingleRange(self):
        self._testBase(1, [1])

    def testMultipleBytesSingleRange(self):
        self._testBase(4, [1])

    def testMultipleBytesMaximumRange(self):
        self._testBase(4, range(1, 5))

    def testMultipleBytesArbitraryRange(self):
        self._testBase(20, [7, 12, 9, 3, 19])

    def testExceptionIfRangeOverflowsSingleByte(self):
        with self.assertRaises(KittyException):
            ByteFlips('\x00', bytes_range=[2])

    def testExceptionIfUnorderedRangeOverflowsSingleByte(self):
        with self.assertRaises(KittyException):
            ByteFlips('\x00', bytes_range=[2, 1])

    def testExceptionIfRangeOverflowsMultipleBytes(self):
        with self.assertRaises(KittyException):
            ByteFlips('\x00' * 10, bytes_range=[11])

    def testExceptionIfUnorderedRangeOverflowsMultipleBytes(self):
        with self.assertRaises(KittyException):
            ByteFlips('\x00' * 10, bytes_range=[3, 11, 7])
