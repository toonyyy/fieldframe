"""
Tests for fieldframe.fields.compute — ComputedField class.
"""

import pytest
from fieldframe.fields.compute import ComputedField
from fieldframe.types.int import uint_type, int_type


# ---------------------------------------------------------------------------
# Shared compute functions
# ---------------------------------------------------------------------------


def always_42(fields):
    return 42


def always_0(fields):
    return 0


def count_fields(fields):
    return len(fields)


def xor_of_writes(fields):
    """XOR all sibling write values, skipping fields named 'checksum'."""
    acc = 0
    for f in fields:
        if hasattr(f, "write") and getattr(f, "name", None) != "checksum":
            acc ^= f.write or 0
    return acc & 0xFF


class _FakeField:
    """Minimal stand-in for a sibling field in compute function tests."""

    def __init__(self, name: str, write: int):
        self.name = name
        self.write = write


# ===========================================================================
# Construction
# ===========================================================================


class TestComputedFieldConstruction:
    def test_name_is_none_by_default(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.name is None

    def test_name_set(self):
        cf = ComputedField(name="checksum", type=uint_type(8), compute=always_42)
        assert cf.name == "checksum"

    def test_compute_stored(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.compute is always_42

    def test_default_zero(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.default == 0

    def test_write_equals_default_before_encode(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.write == 0  # default; compute not yet called

    def test_read_is_none_initially(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.read is None

    def test_type_defaults_to_uint8_when_none(self):
        cf = ComputedField(compute=always_42)
        assert cf.type.bits == 8
        assert cf.type.signed is False

    def test_explicit_type_stored(self):
        cf = ComputedField(type=uint_type(16), compute=always_42)
        assert cf.type.bits == 16


# ===========================================================================
# length()
# ===========================================================================


class TestComputedFieldLength:
    def test_length_uint8(self):
        assert ComputedField(type=uint_type(8), compute=always_42).length() == 8

    def test_length_uint16(self):
        assert ComputedField(type=uint_type(16), compute=always_42).length() == 16

    def test_length_uint32(self):
        assert ComputedField(type=uint_type(32), compute=always_42).length() == 32

    def test_length_int32(self):
        assert ComputedField(type=int_type(32), compute=always_0).length() == 32


# ===========================================================================
# write property
# ===========================================================================


class TestComputedFieldWriteProperty:
    def test_write_is_default_before_encode(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.write == 0

    def test_write_reflects_computed_value_after_encode(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        cf._encode_bits("big")
        assert cf.write == 42

    def test_write_updates_on_each_encode(self):
        counter = [0]

        def incrementing(fields):
            counter[0] += 1
            return counter[0] % 256

        cf = ComputedField(type=uint_type(8), compute=incrementing)
        cf._encode_bits("big")
        assert cf.write == 1
        cf._encode_bits("big")
        assert cf.write == 2


# ===========================================================================
# _encode_bits
# ===========================================================================


class TestComputedFieldEncode:
    def test_encode_calls_compute_function(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        encoded = cf._encode_bits("big")
        assert len(encoded) == 8
        assert set(encoded) <= {"0", "1"}

    def test_known_encoding_42(self):
        # 42 = 0b00101010
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf._encode_bits("big") == "00101010"

    def test_known_encoding_zero(self):
        cf = ComputedField(type=uint_type(8), compute=always_0)
        assert cf._encode_bits("big") == "00000000"

    def test_encode_passes_fields_list_to_compute(self):
        received = []

        def capture(fields):
            received.extend(fields)
            return 0

        cf = ComputedField(type=uint_type(8), compute=capture)
        sentinel = _FakeField("payload", 99)
        cf._encode_bits("big", fields=[sentinel])
        assert sentinel in received

    def test_encode_empty_fields_list_by_default(self):
        # count_fields([]) = 0
        cf = ComputedField(type=uint_type(8), compute=count_fields)
        assert cf._encode_bits("big") == "00000000"

    def test_encode_uses_supplied_fields(self):
        # count_fields([a, b, c]) = 3
        cf = ComputedField(type=uint_type(8), compute=count_fields)
        fields = [_FakeField(f"f{i}", 0) for i in range(3)]
        encoded = cf._encode_bits("big", fields=fields)
        # 3 = 0b00000011
        assert encoded == "00000011"

    def test_encode_persists_computed_value_as_write(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.write == 0  # before
        cf._encode_bits("big")
        assert cf.write == 42  # after

    def test_encode_raises_if_compute_returns_out_of_range(self):
        def out_of_range(fields):
            return 999  # too large for uint8

        cf = ComputedField(type=uint_type(8), compute=out_of_range)
        with pytest.raises(ValueError):
            cf._encode_bits("big")

    def test_encode_xor_checksum(self):
        fields = [_FakeField("payload", 0xAB), _FakeField("checksum", 0)]
        cf = ComputedField(name="checksum", type=uint_type(8), compute=xor_of_writes)
        cf._encode_bits("big", fields=fields)
        # payload=0xAB; checksum skipped → acc = 0xAB = 171
        assert cf.write == 0xAB

    def test_encode_big_vs_little_differ_multibyte(self):
        def return_256(fields):
            return 256

        cf = ComputedField(type=uint_type(16), compute=return_256)
        big = cf._encode_bits("big")
        little = cf._encode_bits("little")
        assert big != little

    def test_encode_single_byte_endian_no_difference(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf._encode_bits("big") == cf._encode_bits("little")

    def test_encode_length_matches_type_bits(self):
        cf = ComputedField(type=uint_type(16), compute=always_0)
        assert len(cf._encode_bits("big")) == 16


# ===========================================================================
# _decode_bits
# ===========================================================================


class TestComputedFieldDecode:
    def test_decode_sets_read(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        assert cf.read is None
        cf._decode_bits("00101010", "big")  # 42
        assert cf.read == 42

    def test_decode_returns_decoded_value(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        result = cf._decode_bits("11111111", "big")
        assert result == 255

    def test_decode_does_not_call_compute(self):
        called = []

        def track(fields):
            called.append(True)
            return 0

        cf = ComputedField(type=uint_type(8), compute=track)
        cf._decode_bits("00000000", "big")
        assert called == [], "compute must NOT be called during decode"

    def test_decode_overwrites_previous_read(self):
        cf = ComputedField(type=uint_type(8), compute=always_42)
        cf._decode_bits("00000001", "big")  # 1
        assert cf.read == 1
        cf._decode_bits("11111110", "big")  # 254
        assert cf.read == 254

    def test_round_trip_big_endian(self):
        cf_enc = ComputedField(type=uint_type(8), compute=always_42)
        encoded = cf_enc._encode_bits("big")

        cf_dec = ComputedField(type=uint_type(8), compute=always_42)
        cf_dec._decode_bits(encoded, "big")
        assert cf_dec.read == 42

    def test_round_trip_little_endian_multibyte(self):
        def return_256(fields):
            return 256

        cf_enc = ComputedField(type=uint_type(16), compute=return_256)
        encoded = cf_enc._encode_bits("little")

        cf_dec = ComputedField(type=uint_type(16), compute=return_256)
        cf_dec._decode_bits(encoded, "little")
        assert cf_dec.read == 256

    def test_decode_uint8_zero(self):
        cf = ComputedField(type=uint_type(8), compute=always_0)
        result = cf._decode_bits("00000000", "big")
        assert result == 0

    def test_decode_uint8_255(self):
        cf = ComputedField(type=uint_type(8), compute=always_0)
        result = cf._decode_bits("11111111", "big")
        assert result == 255


# ===========================================================================
# Display
# ===========================================================================


class TestComputedFieldDisplay:
    def test_repr_contains_name(self):
        cf = ComputedField(name="checksum", type=uint_type(8), compute=always_42)
        assert "checksum" in repr(cf)

    def test_repr_contains_type(self):
        cf = ComputedField(name="checksum", type=uint_type(8), compute=always_42)
        assert "uint8" in repr(cf)

    def test_repr_contains_function_name(self):
        cf = ComputedField(name="checksum", type=uint_type(8), compute=always_42)
        assert "always_42" in repr(cf)

    def test_repr_lambda_shown(self):
        cf = ComputedField(type=uint_type(8), compute=lambda f: 0)
        assert "<lambda>" in repr(cf)

    def test_repr_read_none_shown_as_dash(self):
        cf = ComputedField(name="checksum", type=uint_type(8), compute=always_42)
        assert "—" in repr(cf)

    def test_repr_read_shown_after_decode(self):
        cf = ComputedField(name="checksum", type=uint_type(8), compute=always_42)
        cf._decode_bits("00101010", "big")  # 42
        assert "42" in repr(cf)

    def test_str_contains_name(self):
        cf = ComputedField(name="crc", type=uint_type(16), compute=always_42)
        assert "crc" in str(cf)

    def test_str_contains_fn_label(self):
        cf = ComputedField(name="crc", type=uint_type(8), compute=always_42)
        assert "always_42" in str(cf)
