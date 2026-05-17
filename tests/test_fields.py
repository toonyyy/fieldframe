"""
Tests for fieldframe.fields.field — Field class.
"""

import pytest
from fieldframe.fields.field import Field
from fieldframe.types.int import IntType, uint_type, int_type
from fieldframe.types.float import FloatType, single_type, double_type
from fieldframe.types.string import StringType


# ===========================================================================
# Construction
# ===========================================================================

class TestFieldConstruction:
    def test_name_is_none_by_default(self):
        f = Field(type=uint_type(8))
        assert f.name is None

    def test_name_set(self):
        f = Field(name="speed", type=uint_type(8))
        assert f.name == "speed"

    def test_type_stored(self):
        t = uint_type(16)
        f = Field(type=t)
        assert f.type is t

    def test_default_zero(self):
        f = Field(type=uint_type(8))
        assert f.write == 0

    def test_custom_default(self):
        f = Field(type=uint_type(8), default=42)
        assert f.write == 42

    def test_read_is_none_initially(self):
        f = Field(type=uint_type(8))
        assert f.read is None

    def test_invalid_default_raises_value_error(self):
        with pytest.raises(ValueError):
            Field(type=uint_type(8), default=256)

    def test_invalid_default_type_raises_type_error(self):
        with pytest.raises(TypeError):
            Field(type=uint_type(8), default=1.5)

    def test_float_type_default_zero(self):
        # int 0 is accepted by FloatType.validate
        f = Field(type=single_type(), default=0)
        assert f.write == 0

    def test_float_type_float_default(self):
        f = Field(type=single_type(), default=3.14)
        assert f.write == pytest.approx(3.14)

    def test_string_type_default(self):
        f = Field(type=StringType(length=8), default="")
        assert f.write == ""


# ===========================================================================
# length()
# ===========================================================================

class TestFieldLength:
    def test_length_uint8(self):
        assert Field(type=uint_type(8)).length() == 8

    def test_length_uint16(self):
        assert Field(type=uint_type(16)).length() == 16

    def test_length_int32(self):
        assert Field(type=int_type(32)).length() == 32

    def test_length_float32(self):
        assert Field(type=single_type()).length() == 32

    def test_length_float64(self):
        assert Field(type=double_type()).length() == 64

    def test_length_string_4_bytes(self):
        assert Field(type=StringType(length=4), default="").length() == 32  # 4 × 8

    def test_length_string_8_bytes(self):
        assert Field(type=StringType(length=8), default="").length() == 64


# ===========================================================================
# write property
# ===========================================================================

class TestFieldWriteProperty:
    def test_write_setter_valid_value(self):
        f = Field(type=uint_type(8))
        f.write = 100
        assert f.write == 100

    def test_write_setter_min_boundary(self):
        f = Field(type=int_type(8))
        f.write = -128
        assert f.write == -128

    def test_write_setter_max_boundary(self):
        f = Field(type=uint_type(8))
        f.write = 255
        assert f.write == 255

    def test_write_below_min_raises(self):
        f = Field(type=uint_type(8))
        with pytest.raises(ValueError):
            f.write = -1

    def test_write_above_max_raises(self):
        f = Field(type=uint_type(8))
        with pytest.raises(ValueError):
            f.write = 256

    def test_write_wrong_type_raises_type_error(self):
        f = Field(type=uint_type(8))
        with pytest.raises(TypeError):
            f.write = 1.5

    def test_write_none_raises(self):
        f = Field(type=uint_type(8))
        with pytest.raises(TypeError):
            f.write = None

    def test_write_decimal_string_converted(self):
        f = Field(type=uint_type(8))
        f.write = "42"
        assert f.write == 42

    def test_write_hex_string_converted(self):
        f = Field(type=uint_type(8))
        f.write = "0xFF"
        assert f.write == 255

    def test_write_invalid_string_raises(self):
        f = Field(type=uint_type(8))
        with pytest.raises(ValueError):
            f.write = "not_a_number"

    def test_write_float_field_accepts_float(self):
        f = Field(type=single_type(), default=0.0)
        f.write = 3.14
        assert f.write == pytest.approx(3.14)

    def test_write_float_field_accepts_int(self):
        f = Field(type=single_type(), default=0.0)
        f.write = 5
        assert f.write == 5

    def test_write_string_field_accepts_string(self):
        f = Field(type=StringType(length=8), default="")
        f.write = "hello"
        assert f.write == "hello"

    def test_write_string_field_too_long_raises(self):
        f = Field(type=StringType(length=4), default="")
        with pytest.raises(ValueError):
            f.write = "toolong"


# ===========================================================================
# _encode_bits / _decode_bits
# ===========================================================================

class TestFieldEncodeDecode:
    @pytest.mark.parametrize("value,bits,signed,endian", [
        (0,     8,  False, "big"),
        (255,   8,  False, "big"),
        (0,     8,  False, "little"),
        (-128,  8,  True,  "big"),
        (127,   8,  True,  "big"),
        (-1,    8,  True,  "little"),
        (1000,  16, False, "big"),
        (1000,  16, False, "little"),
        (-32768, 16, True,  "big"),
        (0,     32, False, "big"),
        (0,     32, False, "little"),
    ])
    def test_int_round_trip(self, value, bits, signed, endian):
        t = IntType(bits=bits, signed=signed)
        f = Field(type=t, default=t.min_value)
        f.write = value
        encoded = f._encode_bits(endian)
        assert len(encoded) == bits
        assert set(encoded) <= {"0", "1"}
        decoded = f._decode_bits(encoded, endian)
        assert decoded == value
        assert f.read == value

    def test_float_round_trip_big(self):
        f = Field(type=single_type(), default=0.0)
        f.write = 3.14
        encoded = f._encode_bits("big")
        assert len(encoded) == 32
        decoded = f._decode_bits(encoded, "big")
        assert decoded == pytest.approx(3.14, rel=1e-5)
        assert f.read == pytest.approx(3.14, rel=1e-5)

    def test_float_round_trip_little(self):
        f = Field(type=single_type(), default=0.0)
        f.write = -273.15
        encoded = f._encode_bits("little")
        decoded = f._decode_bits(encoded, "little")
        assert decoded == pytest.approx(-273.15, rel=1e-5)

    def test_string_round_trip(self):
        f = Field(type=StringType(length=8), default="")
        f.write = "hello"
        encoded = f._encode_bits("big")
        assert len(encoded) == 64
        decoded = f._decode_bits(encoded, "big")
        assert decoded == "hello"
        assert f.read == "hello"

    def test_decode_sets_read(self):
        f = Field(type=uint_type(8), default=0)
        assert f.read is None
        f._decode_bits("01100011", "big")  # 99
        assert f.read == 99

    def test_encode_length_matches_type_bits(self):
        f = Field(type=uint_type(16), default=0)
        assert len(f._encode_bits("big")) == 16

    def test_big_endian_vs_little_differ_multibyte(self):
        f = Field(type=uint_type(16), default=256)
        assert f._encode_bits("big") != f._encode_bits("little")

    def test_single_byte_endian_no_difference(self):
        f = Field(type=uint_type(8), default=42)
        assert f._encode_bits("big") == f._encode_bits("little")

    def test_known_encoding_uint8_one(self):
        f = Field(type=uint_type(8), default=1)
        assert f._encode_bits("big") == "00000001"

    def test_known_encoding_uint8_255(self):
        f = Field(type=uint_type(8), default=255)
        assert f._encode_bits("big") == "11111111"

    def test_known_encoding_int8_neg1(self):
        f = Field(type=int_type(8), default=-1)
        assert f._encode_bits("big") == "11111111"

    def test_known_encoding_int8_neg128(self):
        f = Field(type=int_type(8), default=-128)
        assert f._encode_bits("big") == "10000000"

    def test_known_encoding_uint8_99(self):
        f = Field(name="speed", type=uint_type(8), default=99)
        assert f._encode_bits("big") == "01100011"


# ===========================================================================
# Display
# ===========================================================================

class TestFieldDisplay:
    def test_repr_contains_name(self):
        f = Field(name="speed", type=uint_type(8), default=0)
        assert "speed" in repr(f)

    def test_repr_contains_type(self):
        f = Field(name="speed", type=uint_type(8), default=0)
        assert "uint8" in repr(f)

    def test_repr_contains_write_value(self):
        f = Field(name="speed", type=uint_type(8), default=99)
        assert "99" in repr(f)

    def test_repr_read_none_shown_as_dash(self):
        f = Field(name="speed", type=uint_type(8), default=0)
        assert "—" in repr(f)

    def test_repr_read_shown_after_decode(self):
        f = Field(name="speed", type=uint_type(8), default=0)
        f._decode_bits("00000001", "big")
        assert "1" in repr(f)

    def test_str_contains_name(self):
        f = Field(name="altitude", type=uint_type(16), default=0)
        assert "altitude" in str(f)

    def test_str_contains_type(self):
        f = Field(name="altitude", type=uint_type(16), default=0)
        assert "uint16" in str(f)

    def test_str_unnamed_placeholder(self):
        f = Field(type=uint_type(8))
        assert "unnamed" in str(f)