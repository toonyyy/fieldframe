"""
Tests for fieldframe.types.string
"""

import pytest
from fieldframe import StringType, ascii_type, utf8_type


# ===========================================================================
# StringType construction
# ===========================================================================

class TestStringTypeConstruction:
    def test_valid_defaults(self):
        t = StringType(length=8)
        assert t.length == 8
        assert t.encoding == "ascii"
        assert t.pad == "\x00"

    def test_custom_encoding(self):
        t = StringType(length=16, encoding="utf-8")
        assert t.encoding == "utf-8"

    def test_custom_pad(self):
        t = StringType(length=8, pad=" ")
        assert t.pad == " "

    def test_length_1_valid(self):
        t = StringType(length=1)
        assert t.length == 1

    def test_length_zero_raises(self):
        with pytest.raises(ValueError, match="length must be >= 1"):
            StringType(length=0)

    def test_length_negative_raises(self):
        with pytest.raises(ValueError):
            StringType(length=-1)

    def test_pad_multibyte_raises(self):
        # A character that encodes to more than 1 byte under ascii is invalid
        with pytest.raises(ValueError):
            StringType(length=8, encoding="ascii", pad="é")

    def test_pad_unencodable_raises(self):
        with pytest.raises(ValueError):
            StringType(length=8, encoding="ascii", pad="€")

    def test_immutable(self):
        t = StringType(length=8)
        with pytest.raises(Exception):
            t.length = 16

    def test_hashable(self):
        t1 = StringType(length=8)
        t2 = StringType(length=8)
        assert hash(t1) == hash(t2)
        assert t1 == t2

    def test_different_lengths_not_equal(self):
        assert StringType(length=8) != StringType(length=16)

    def test_different_encodings_not_equal(self):
        assert StringType(length=8, encoding="ascii") != StringType(length=8, encoding="utf-8")

    def test_different_pads_not_equal(self):
        assert StringType(length=8, pad="\x00") != StringType(length=8, pad=" ")


# ===========================================================================
# bits property
# ===========================================================================

class TestStringTypeBits:
    def test_bits_is_length_times_8(self):
        assert StringType(length=1).bits == 8
        assert StringType(length=4).bits == 32
        assert StringType(length=16).bits == 128

    def test_bits_matches_encoded_length(self):
        t = StringType(length=8)
        encoded = t.encode_bits("hi", "big")
        assert len(encoded) == t.bits


# ===========================================================================
# Validate
# ===========================================================================

class TestStringTypeValidate:
    def test_empty_string_valid(self):
        t = StringType(length=8)
        assert t.validate("") is True

    def test_exact_length_valid(self):
        t = StringType(length=5)
        assert t.validate("hello") is True

    def test_shorter_than_length_valid(self):
        t = StringType(length=8)
        assert t.validate("hi") is True

    def test_too_long_raises_value_error(self):
        t = StringType(length=4)
        with pytest.raises(ValueError, match="bytes"):
            t.validate("toolong")

    def test_non_string_raises_type_error(self):
        t = StringType(length=8)
        with pytest.raises(TypeError, match="Expected str"):
            t.validate(42)

    def test_none_raises_type_error(self):
        t = StringType(length=8)
        with pytest.raises(TypeError):
            t.validate(None)

    def test_unencodable_raises_value_error(self):
        t = StringType(length=8)  # ascii by default
        with pytest.raises(ValueError, match="cannot be encoded"):
            t.validate("héllo")

    def test_utf8_accepts_multibyte_chars(self):
        t = utf8_type(8)
        # "€" is 3 bytes in UTF-8, so fits in an 8-byte field
        assert t.validate("€") is True

    def test_utf8_too_long_raises(self):
        t = utf8_type(2)
        # "€" is 3 bytes in UTF-8, won't fit in 2 bytes
        with pytest.raises(ValueError, match="bytes"):
            t.validate("€")

    def test_latin1_accepts_extended_ascii(self):
        t = StringType(length=4, encoding="latin-1")
        assert t.validate("café"[:3]) is True  # 3 latin-1 chars

    def test_exact_byte_boundary_utf8(self):
        # 4 ASCII chars = 4 bytes, fits in utf8_type(4)
        t = utf8_type(4)
        assert t.validate("abcd") is True


# ===========================================================================
# Encode / decode round-trips
# ===========================================================================

class TestStringTypeEncodeDecode:
    @pytest.mark.parametrize("value,length,encoding,pad,endian", [
        ("hello",  8, "ascii",  "\x00", "big"),
        ("hello",  8, "ascii",  "\x00", "little"),
        ("",       4, "ascii",  "\x00", "big"),
        ("hi",     4, "ascii",  " ",    "big"),
        ("test",   4, "ascii",  "\x00", "big"),
        ("ABCDEF", 6, "ascii",  "\x00", "big"),
        ("héllo",  8, "utf-8",  "\x00", "big"),
        ("",       8, "utf-8",  "\x00", "little"),
    ])
    def test_round_trip(self, value, length, encoding, pad, endian):
        t = StringType(length=length, encoding=encoding, pad=pad)
        encoded = t.encode_bits(value, endian)
        assert len(encoded) == length * 8
        assert set(encoded) <= {"0", "1"}
        decoded = t.decode_bits(encoded, endian)
        assert decoded == value

    def test_endian_has_no_effect(self):
        t = StringType(length=8)
        big = t.encode_bits("hello", "big")
        little = t.encode_bits("hello", "little")
        assert big == little

    def test_short_string_padded_to_full_width(self):
        t = StringType(length=4)
        encoded = t.encode_bits("hi", "big")
        assert len(encoded) == 32  # 4 bytes × 8

    def test_pad_stripped_on_decode(self):
        t = StringType(length=8)
        encoded = t.encode_bits("hi", "big")
        decoded = t.decode_bits(encoded, "big")
        assert decoded == "hi"  # no trailing nulls

    def test_space_pad_stripped_on_decode(self):
        t = StringType(length=8, encoding="ascii", pad=" ")
        encoded = t.encode_bits("hi", "big")
        decoded = t.decode_bits(encoded, "big")
        assert decoded == "hi"

    def test_empty_string_round_trip(self):
        t = StringType(length=4)
        encoded = t.encode_bits("", "big")
        decoded = t.decode_bits(encoded, "big")
        assert decoded == ""

    def test_exact_fit_no_padding_needed(self):
        t = StringType(length=5)
        encoded = t.encode_bits("hello", "big")
        decoded = t.decode_bits(encoded, "big")
        assert decoded == "hello"

    def test_utf8_multibyte_round_trip(self):
        t = utf8_type(16)
        value = "héllo"
        encoded = t.encode_bits(value, "big")
        assert len(encoded) == 128
        decoded = t.decode_bits(encoded, "big")
        assert decoded == value

    def test_known_encoding_ascii_a(self):
        t = StringType(length=1)
        # 'A' = 0x41 = 0b01000001
        assert t.encode_bits("A", "big") == "01000001"

    def test_all_null_decodes_to_empty(self):
        t = StringType(length=4)
        all_null = "0" * 32
        assert t.decode_bits(all_null, "big") == ""

    def test_all_space_pad_decodes_to_empty(self):
        t = StringType(length=4, encoding="ascii", pad=" ")
        # 4 space bytes
        space_bits = "00100000" * 4
        assert t.decode_bits(space_bits, "big") == ""


# ===========================================================================
# Display
# ===========================================================================

class TestStringTypeDisplay:
    def test_str_ascii(self):
        assert str(StringType(length=8)) == "ascii/8"

    def test_str_utf8(self):
        assert str(StringType(length=16, encoding="utf-8")) == "utf-8/16"

    def test_repr_contains_encoding(self):
        r = repr(StringType(length=8))
        assert "ascii" in r

    def test_repr_contains_length(self):
        r = repr(StringType(length=8))
        assert "8 bytes" in r

    def test_repr_contains_pad_null(self):
        r = repr(StringType(length=8, pad="\x00"))
        # null pad shown as repr
        assert "\\x00" in r

    def test_repr_contains_pad_space(self):
        r = repr(StringType(length=8, pad=" "))
        assert "pad= " in r


# ===========================================================================
# Convenience factories
# ===========================================================================

class TestFactories:
    def test_ascii_type(self):
        t = ascii_type(8)
        assert isinstance(t, StringType)
        assert t.encoding == "ascii"
        assert t.pad == "\x00"
        assert t.length == 8

    def test_ascii_type_custom_pad(self):
        t = ascii_type(8, pad=" ")
        assert t.pad == " "

    def test_utf8_type(self):
        t = utf8_type(32)
        assert isinstance(t, StringType)
        assert t.encoding == "utf-8"
        assert t.length == 32
        assert t.pad == "\x00"

    def test_utf8_type_custom_pad(self):
        t = utf8_type(8, pad=" ")
        assert t.pad == " "

    def test_factories_return_string_type(self):
        assert isinstance(ascii_type(4), StringType)
        assert isinstance(utf8_type(4), StringType)