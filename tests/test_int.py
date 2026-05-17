"""
Tests for fieldframe.types.int
"""

import pytest
from fieldframe.types.int import IntType, int_type, uint_type


# ===========================================================================
# IntType construction
# ===========================================================================


class TestIntTypeConstruction:
    def test_valid_unsigned(self):
        t = IntType(bits=8, signed=False)
        assert t.bits == 8
        assert t.signed is False

    def test_valid_signed(self):
        t = IntType(bits=16, signed=True)
        assert t.bits == 16
        assert t.signed is True

    def test_bits_1(self):
        # 1-bit unsigned: only 0 and 1
        t = IntType(bits=1, signed=False)
        assert t.min_value == 0
        assert t.max_value == 1

    def test_bits_1_signed(self):
        # 1-bit signed: only 0 and -1
        t = IntType(bits=1, signed=True)
        assert t.min_value == -1
        assert t.max_value == 0

    def test_bits_64(self):
        t = IntType(bits=64, signed=False)
        assert t.max_value == 2**64 - 1

    def test_bits_zero_raises(self):
        with pytest.raises(ValueError, match="bits must be >= 1"):
            IntType(bits=0, signed=False)

    def test_bits_negative_raises(self):
        with pytest.raises(ValueError):
            IntType(bits=-1, signed=False)

    def test_bits_65_raises(self):
        with pytest.raises(ValueError, match="bits must be <= 64"):
            IntType(bits=65, signed=False)

    def test_immutable(self):
        t = IntType(bits=8, signed=False)
        with pytest.raises(Exception):
            t.bits = 16  # frozen dataclass

    def test_hashable(self):
        t1 = IntType(bits=8, signed=False)
        t2 = IntType(bits=8, signed=False)
        assert hash(t1) == hash(t2)
        assert t1 == t2

    def test_different_types_not_equal(self):
        assert IntType(bits=8, signed=True) != IntType(bits=8, signed=False)
        assert IntType(bits=8, signed=True) != IntType(bits=16, signed=True)


# ===========================================================================
# Range properties
# ===========================================================================


class TestIntTypeRange:
    @pytest.mark.parametrize(
        "bits,expected_min,expected_max",
        [
            (8, -128, 127),
            (16, -32768, 32767),
            (32, -2147483648, 2147483647),
        ],
    )
    def test_signed_range(self, bits, expected_min, expected_max):
        t = IntType(bits=bits, signed=True)
        assert t.min_value == expected_min
        assert t.max_value == expected_max

    @pytest.mark.parametrize(
        "bits,expected_max",
        [
            (8, 255),
            (16, 65535),
            (32, 4294967295),
        ],
    )
    def test_unsigned_range(self, bits, expected_max):
        t = IntType(bits=bits, signed=False)
        assert t.min_value == 0
        assert t.max_value == expected_max


# ===========================================================================
# Validate
# ===========================================================================


class TestIntTypeValidate:
    def test_valid_value_returns_true(self):
        t = uint_type(8)
        assert t.validate(0) is True
        assert t.validate(128) is True
        assert t.validate(255) is True

    def test_valid_signed_extremes(self):
        t = int_type(8)
        assert t.validate(-128) is True
        assert t.validate(127) is True

    def test_below_min_raises(self):
        t = uint_type(8)
        with pytest.raises(ValueError, match="out of range"):
            t.validate(-1)

    def test_above_max_raises(self):
        t = uint_type(8)
        with pytest.raises(ValueError, match="out of range"):
            t.validate(256)

    def test_wrong_type_raises_type_error(self):
        t = uint_type(8)
        with pytest.raises(TypeError, match="Expected int"):
            t.validate(1.5)

    def test_string_raises_type_error(self):
        t = uint_type(8)
        with pytest.raises(TypeError):
            t.validate("42")

    def test_none_raises_type_error(self):
        t = uint_type(8)
        with pytest.raises(TypeError):
            t.validate(None)

    def test_bool_is_accepted(self):
        # bool is a subclass of int in Python
        t = uint_type(8)
        assert t.validate(True) is True
        assert t.validate(False) is True


# ===========================================================================
# Encode / decode round-trips
# ===========================================================================


class TestIntTypeEncodeDecode:
    @pytest.mark.parametrize(
        "value,bits,signed,endian",
        [
            (0, 8, False, "big"),
            (255, 8, False, "big"),
            (0, 8, False, "little"),
            (255, 8, False, "little"),
            (-128, 8, True, "big"),
            (127, 8, True, "big"),
            (1000, 16, False, "big"),
            (1000, 16, False, "little"),
            (-1, 16, True, "big"),
            (-1, 16, True, "little"),
            (0, 32, True, "big"),
            (0, 32, True, "little"),
        ],
    )
    def test_round_trip(self, value, bits, signed, endian):
        t = IntType(bits=bits, signed=signed)
        encoded = t.encode_bits(value, endian)
        assert len(encoded) == bits
        assert set(encoded) <= {"0", "1"}
        decoded = t.decode_bits(encoded, endian)
        assert decoded == value

    def test_encode_produces_correct_length(self):
        t = uint_type(16)
        assert len(t.encode_bits(0, "big")) == 16

    def test_big_endian_vs_little_endian_differ_for_multibyte(self):
        t = uint_type(16)
        big = t.encode_bits(256, "big")
        little = t.encode_bits(256, "little")
        assert big != little

    def test_single_byte_endian_does_not_matter(self):
        t = uint_type(8)
        assert t.encode_bits(42, "big") == t.encode_bits(42, "little")

    def test_known_encoding_uint8(self):
        t = uint_type(8)
        assert t.encode_bits(1, "big") == "00000001"
        assert t.encode_bits(255, "big") == "11111111"
        assert t.encode_bits(0, "big") == "00000000"

    def test_known_encoding_int8_negative(self):
        t = int_type(8)
        # -1 in two's complement is 0xFF
        assert t.encode_bits(-1, "big") == "11111111"
        # -128 in two's complement is 0x80
        assert t.encode_bits(-128, "big") == "10000000"


# ===========================================================================
# Display
# ===========================================================================


class TestIntTypeDisplay:
    def test_str_unsigned(self):
        assert str(IntType(bits=8, signed=False)) == "uint8"

    def test_str_signed(self):
        assert str(IntType(bits=16, signed=True)) == "int16"

    def test_repr_unsigned(self):
        r = repr(IntType(bits=8, signed=False))
        assert "uint8" in r
        assert "0" in r
        assert "255" in r

    def test_repr_signed(self):
        r = repr(IntType(bits=16, signed=True))
        assert "int16" in r
        assert "-32768" in r
        assert "32767" in r


# ===========================================================================
# Convenience factories
# ===========================================================================


class TestFactories:
    def test_int_type_is_signed(self):
        t = int_type(8)
        assert t.signed is True
        assert t.bits == 8

    def test_uint_type_is_unsigned(self):
        t = uint_type(8)
        assert t.signed is False
        assert t.bits == 8

    def test_int_type_repr(self):
        t = int_type(8)
        assert "int8" in repr(t)
        assert "-128" in repr(t)

    def test_uint_type_repr(self):
        t = uint_type(8)
        assert "uint8" in repr(t)
        assert "255" in repr(t)

    def test_factories_return_int_type(self):
        assert isinstance(int_type(16), IntType)
        assert isinstance(uint_type(32), IntType)
