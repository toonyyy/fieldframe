"""
Tests for fieldframe.types.float
"""

import math
import struct
import pytest
from fieldframe.types.float import (
    FloatType,
    float_type,
    half_type,
    single_type,
    double_type,
)


# ===========================================================================
# FloatType construction
# ===========================================================================


class TestFloatTypeConstruction:
    def test_valid_16(self):
        t = FloatType(bits=16)
        assert t.bits == 16

    def test_valid_32(self):
        t = FloatType(bits=32)
        assert t.bits == 32

    def test_valid_64(self):
        t = FloatType(bits=64)
        assert t.bits == 64

    def test_invalid_bits_raises(self):
        with pytest.raises(ValueError, match="16, 32, or 64"):
            FloatType(bits=8)

    def test_invalid_bits_zero_raises(self):
        with pytest.raises(ValueError):
            FloatType(bits=0)

    def test_allow_special_default_false(self):
        t = FloatType(bits=32)
        assert t.allow_special is False

    def test_allow_special_true(self):
        t = FloatType(bits=32, allow_special=True)
        assert t.allow_special is True

    def test_immutable(self):
        t = FloatType(bits=32)
        with pytest.raises(Exception):
            t.bits = 64

    def test_hashable(self):
        t1 = FloatType(bits=32)
        t2 = FloatType(bits=32)
        assert hash(t1) == hash(t2)

    def test_allow_special_excluded_from_equality(self):
        # allow_special has compare=False, so two types differing only by it are equal
        t1 = FloatType(bits=32, allow_special=False)
        t2 = FloatType(bits=32, allow_special=True)
        assert t1 == t2


# ===========================================================================
# Range properties
# ===========================================================================


class TestFloatTypeRange:
    def test_float16_max(self):
        t = FloatType(bits=16)
        assert t.max_value == 65504.0

    def test_float16_min(self):
        t = FloatType(bits=16)
        assert t.min_value == -65504.0

    def test_float32_max(self):
        t = FloatType(bits=32)
        expected = struct.unpack(">f", b"\x7f\x7f\xff\xff")[0]
        assert t.max_value == pytest.approx(expected)

    def test_float32_min(self):
        t = FloatType(bits=32)
        assert t.min_value == -t.max_value

    def test_float64_max(self):
        t = FloatType(bits=64)
        expected = struct.unpack(">d", b"\x7f\xef\xff\xff\xff\xff\xff\xff")[0]
        assert t.max_value == pytest.approx(expected)

    def test_max_is_finite(self):
        for bits in (16, 32, 64):
            t = FloatType(bits=bits)
            assert math.isfinite(t.max_value)
            assert math.isfinite(t.min_value)


# ===========================================================================
# Validate
# ===========================================================================


class TestFloatTypeValidate:
    def test_valid_zero(self):
        assert FloatType(bits=32).validate(0.0) is True

    def test_valid_positive(self):
        assert FloatType(bits=32).validate(1.5) is True

    def test_valid_negative(self):
        assert FloatType(bits=32).validate(-1.5) is True

    def test_valid_int_accepted(self):
        # ints should be accepted (cast to float at encode time)
        assert FloatType(bits=32).validate(42) is True

    def test_valid_at_max(self):
        t = FloatType(bits=32)
        assert t.validate(t.max_value) is True

    def test_valid_at_min(self):
        t = FloatType(bits=32)
        assert t.validate(t.min_value) is True

    def test_nan_rejected_by_default(self):
        t = FloatType(bits=32)
        with pytest.raises(ValueError, match="NaN"):
            t.validate(float("nan"))

    def test_inf_rejected_by_default(self):
        t = FloatType(bits=32)
        with pytest.raises(ValueError, match="inf"):
            t.validate(float("inf"))

    def test_neg_inf_rejected_by_default(self):
        t = FloatType(bits=32)
        with pytest.raises(ValueError, match="inf"):
            t.validate(float("-inf"))

    def test_nan_allowed_with_flag(self):
        t = FloatType(bits=32, allow_special=True)
        assert t.validate(float("nan")) is True

    def test_inf_allowed_with_flag(self):
        t = FloatType(bits=32, allow_special=True)
        assert t.validate(float("inf")) is True

    def test_wrong_type_raises_type_error(self):
        t = FloatType(bits=32)
        with pytest.raises(TypeError, match="Expected float or int"):
            t.validate("1.0")

    def test_none_raises_type_error(self):
        t = FloatType(bits=32)
        with pytest.raises(TypeError):
            t.validate(None)

    def test_overflow_float16(self):
        t = FloatType(bits=16)
        with pytest.raises(ValueError, match="overflows"):
            t.validate(70000.0)  # beyond 65504

    def test_overflow_negative_float16(self):
        t = FloatType(bits=16)
        with pytest.raises(ValueError, match="overflows"):
            t.validate(-70000.0)


# ===========================================================================
# Encode / decode round-trips
# ===========================================================================


class TestFloatTypeEncodeDecode:
    @pytest.mark.parametrize(
        "value,bits,endian",
        [
            (0.0, 16, "big"),
            (0.0, 16, "little"),
            (1.0, 16, "big"),
            (1.0, 16, "little"),
            (-1.0, 16, "big"),
            (-1.0, 16, "little"),
            (3.14, 32, "big"),
            (3.14, 32, "little"),
            (-273.15, 32, "big"),
            (-273.15, 32, "little"),
            (1.23456789, 64, "big"),
            (1.23456789, 64, "little"),
            (0.0, 64, "big"),
        ],
    )
    def test_round_trip(self, value, bits, endian):
        t = FloatType(bits=bits)
        encoded = t.encode_bits(value, endian)
        assert len(encoded) == bits
        assert set(encoded) <= {"0", "1"}
        decoded = t.decode_bits(encoded, endian)
        assert decoded == pytest.approx(value, rel=1e-5)

    def test_encode_length_16(self):
        t = FloatType(bits=16)
        assert len(t.encode_bits(1.0, "big")) == 16

    def test_encode_length_32(self):
        t = FloatType(bits=32)
        assert len(t.encode_bits(1.0, "big")) == 32

    def test_encode_length_64(self):
        t = FloatType(bits=64)
        assert len(t.encode_bits(1.0, "big")) == 64

    def test_big_endian_differs_from_little_endian(self):
        t = FloatType(bits=32)
        big = t.encode_bits(3.14, "big")
        little = t.encode_bits(3.14, "little")
        assert big != little

    def test_nan_round_trip_with_allow_special(self):
        t = FloatType(bits=32, allow_special=True)
        encoded = t.encode_bits(float("nan"), "big")
        decoded = t.decode_bits(encoded, "big")
        assert math.isnan(decoded)

    def test_inf_round_trip_with_allow_special(self):
        t = FloatType(bits=32, allow_special=True)
        encoded = t.encode_bits(float("inf"), "big")
        decoded = t.decode_bits(encoded, "big")
        assert math.isinf(decoded) and decoded > 0

    def test_int_value_encoded_as_float(self):
        t = FloatType(bits=32)
        # Encoding an int should produce the same bits as its float equivalent
        assert t.encode_bits(1, "big") == t.encode_bits(1.0, "big")

    def test_zero_is_all_zeros(self):
        t = FloatType(bits=32)
        assert t.encode_bits(0.0, "big") == "0" * 32


# ===========================================================================
# Display
# ===========================================================================


class TestFloatTypeDisplay:
    def test_str_float16(self):
        assert str(FloatType(bits=16)) == "float16"

    def test_str_float32(self):
        assert str(FloatType(bits=32)) == "float32"

    def test_str_float64(self):
        assert str(FloatType(bits=64)) == "float64"

    def test_repr_contains_type_name(self):
        r = repr(FloatType(bits=32))
        assert "FloatType" in r
        assert "float32" in r

    def test_repr_contains_range(self):
        r = repr(FloatType(bits=16))
        assert "range=" in r
        assert "65504" in r


# ===========================================================================
# Convenience factories
# ===========================================================================


class TestFactories:
    def test_float_type_32(self):
        t = float_type(32)
        assert isinstance(t, FloatType)
        assert t.bits == 32
        assert t.allow_special is False

    def test_float_type_allow_special(self):
        t = float_type(32, allow_special=True)
        assert t.allow_special is True

    def test_float_type_invalid_bits(self):
        with pytest.raises(ValueError):
            float_type(24)

    def test_half_type(self):
        t = half_type()
        assert t.bits == 16
        assert t.allow_special is False

    def test_single_type(self):
        t = single_type()
        assert t.bits == 32

    def test_double_type(self):
        t = double_type()
        assert t.bits == 64

    def test_half_type_allow_special(self):
        t = half_type(allow_special=True)
        assert t.allow_special is True

    def test_factories_return_float_type(self):
        assert isinstance(half_type(), FloatType)
        assert isinstance(single_type(), FloatType)
        assert isinstance(double_type(), FloatType)
