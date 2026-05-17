"""
Tests for fieldframe.fields.flags — FlagsField class.
"""

import pytest
from fieldframe.fields.flags import FlagsField
from fieldframe.types.int import uint_type, int_type


# ===========================================================================
# Construction
# ===========================================================================

class TestFlagsFieldConstruction:
    def test_name_is_none_by_default(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        assert ff.name is None

    def test_name_set(self):
        ff = FlagsField(type=uint_type(8), flags=["a"], name="status")
        assert ff.name == "status"

    def test_lsb_first_default_false(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        assert ff.lsb_first is False

    def test_lsb_first_true(self):
        ff = FlagsField(type=uint_type(8), flags=["a"], lsb_first=True)
        assert ff.lsb_first is True

    def test_signed_type_raises_type_error(self):
        with pytest.raises(TypeError, match="unsigned"):
            FlagsField(type=int_type(8), flags=["a"])

    def test_too_many_flags_raises_value_error(self):
        with pytest.raises(ValueError, match="Too many"):
            FlagsField(type=uint_type(4), flags=["a", "b", "c", "d", "e"])

    def test_duplicate_flag_names_raise(self):
        with pytest.raises(ValueError, match="unique"):
            FlagsField(type=uint_type(8), flags=["a", "a"])

    def test_exactly_fill_bits_ok(self):
        ff = FlagsField(type=uint_type(4), flags=["a", "b", "c", "d"])
        assert len(ff._names) == 4

    def test_fewer_flags_than_bits_ok(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        assert len(ff._names) == 2

    def test_empty_flags_list_ok(self):
        ff = FlagsField(type=uint_type(8), flags=[])
        assert ff.write == 0

    def test_all_flags_initialised_false(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked", "error"])
        assert all(not v for v in ff._flag_writes.values())

    def test_read_is_none_initially(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        assert ff.read is None


# ===========================================================================
# length()
# ===========================================================================

class TestFlagsFieldLength:
    def test_length_uint8(self):
        assert FlagsField(type=uint_type(8), flags=["a"]).length() == 8

    def test_length_uint16(self):
        assert FlagsField(type=uint_type(16), flags=["a"]).length() == 16

    def test_length_uint32(self):
        assert FlagsField(type=uint_type(32), flags=["a"]).length() == 32


# ===========================================================================
# Attribute access — ff.flag_name / ff.flag_name = True
# ===========================================================================

class TestFlagsFieldAttributeAccess:
    def test_getattr_returns_falsy_proxy_initially(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
        assert bool(ff.armed) is False

    def test_setattr_flag_by_name(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
        ff.armed = True
        assert bool(ff.armed) is True
        assert bool(ff.locked) is False

    def test_setattr_only_named_flag_changes(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b", "c"])
        ff.b = True
        assert bool(ff.a) is False
        assert bool(ff.b) is True
        assert bool(ff.c) is False

    def test_setattr_real_attribute_passes_through(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"])
        ff.name = "status"
        assert ff.name == "status"

    def test_getattr_unknown_flag_raises_attribute_error(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"])
        with pytest.raises(AttributeError):
            _ = ff.nonexistent

    def test_setattr_truthy_coerced_to_true(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff.a = 42        # truthy non-bool
        assert ff["a"] is True

    def test_setattr_falsy_coerced_to_false(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff.a = True
        ff.a = 0         # falsy
        assert ff["a"] is False

    def test_set_then_clear_flag(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"])
        ff.armed = True
        ff.armed = False
        assert bool(ff.armed) is False


# ===========================================================================
# Item access — ff["flag"] / ff["flag"] = True
# ===========================================================================

class TestFlagsFieldItemAccess:
    def test_getitem_initially_false(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        assert ff["a"] is False

    def test_setitem_sets_flag(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff["a"] = True
        assert ff["a"] is True

    def test_setitem_coerces_to_bool(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff["a"] = 99
        assert ff["a"] is True

    def test_getitem_unknown_raises_key_error(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        with pytest.raises(KeyError):
            _ = ff["unknown"]

    def test_setitem_unknown_raises_key_error(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        with pytest.raises(KeyError):
            ff["unknown"] = True

    def test_item_and_attr_access_agree(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"])
        ff.armed = True
        assert ff["armed"] is True
        ff["armed"] = False
        assert bool(ff.armed) is False


# ===========================================================================
# write / read / flag_writes / flag_reads properties
# ===========================================================================

class TestFlagsFieldProperties:
    def test_write_all_false_is_zero(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b", "c"])
        assert ff.write == 0

    def test_write_msb_flag_set(self):
        # First flag (MSB-first) → bit 7 of an 8-bit field = 128
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
        ff.armed = True
        assert ff.write == 128

    def test_write_second_flag_set(self):
        # Second flag → bit 6 of an 8-bit field = 64
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
        ff.locked = True
        assert ff.write == 64

    def test_write_multiple_flags(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
        ff.armed  = True
        ff.locked = True
        assert ff.write == 192  # 128 + 64

    def test_write_lsb_first_flag_zero(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"], lsb_first=True)
        ff.a = True
        assert ff.write == 1   # bit 0

    def test_write_lsb_first_second_flag(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"], lsb_first=True)
        ff.b = True
        assert ff.write == 2   # bit 1

    def test_read_none_before_decode(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        assert ff.read is None

    def test_flag_writes_returns_copy(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        ff.a = True
        fw = ff.flag_writes
        assert fw == {"a": True, "b": False}
        fw["a"] = False          # mutating copy must not affect field
        assert ff["a"] is True

    def test_flag_reads_before_decode_all_false(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        assert ff.flag_reads == {"a": False, "b": False}

    def test_flag_reads_after_decode(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        ff._decode_bits("10000000", "big")
        assert ff.flag_reads["a"] is True
        assert ff.flag_reads["b"] is False


# ===========================================================================
# _encode_bits / _decode_bits
# ===========================================================================

class TestFlagsFieldEncodeDecode:
    def test_encode_all_false_is_all_zeros(self):
        ff = FlagsField(type=uint_type(8), flags=["a","b","c","d","e","f","g","h"])
        assert ff._encode_bits("big") == "00000000"

    def test_encode_msb_flag_set(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked"])
        ff.armed = True
        assert ff._encode_bits("big") == "10000000"

    def test_encode_length_matches_type_bits(self):
        ff = FlagsField(type=uint_type(16), flags=["a"])
        assert len(ff._encode_bits("big")) == 16

    def test_encode_only_bit_chars(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff.a = True
        assert set(ff._encode_bits("big")) <= {"0", "1"}

    def test_known_encoding_ready_flag(self):
        # 4 flags on an 8-bit field: armed=MSB, ..., ready=4th flag → bit 4 = 16
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked", "error", "ready"])
        ff.ready = True
        assert ff._encode_bits("big") == "00010000"

    def test_decode_sets_flag_reads(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        ff._decode_bits("10000000", "big")   # bit 7 set → first flag (MSB-first)
        assert ff.flag_reads["a"] is True
        assert ff.flag_reads["b"] is False

    def test_decode_returns_packed_int(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        result = ff._decode_bits("10000000", "big")
        assert result == 128

    def test_decode_sets_read_property(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff._decode_bits("10000000", "big")
        assert ff.read == 128

    def test_round_trip_msb_first(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked", "error", "ready"])
        ff.armed = True
        ff.ready = True
        encoded = ff._encode_bits("big")

        recv = FlagsField(type=uint_type(8), flags=["armed", "locked", "error", "ready"])
        recv._decode_bits(encoded, "big")
        assert recv.flag_reads["armed"] is True
        assert recv.flag_reads["ready"] is True
        assert recv.flag_reads["locked"] is False
        assert recv.flag_reads["error"] is False

    def test_round_trip_lsb_first(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b", "c"], lsb_first=True)
        ff.a = True
        ff.c = True
        encoded = ff._encode_bits("big")

        recv = FlagsField(type=uint_type(8), flags=["a", "b", "c"], lsb_first=True)
        recv._decode_bits(encoded, "big")
        assert recv.flag_reads["a"] is True
        assert recv.flag_reads["b"] is False
        assert recv.flag_reads["c"] is True

    def test_big_endian_vs_little_differ_multibyte(self):
        ff = FlagsField(type=uint_type(16), flags=["a"])
        ff.a = True
        big    = ff._encode_bits("big")
        little = ff._encode_bits("little")
        assert big != little

    def test_round_trip_little_endian_multibyte(self):
        ff = FlagsField(type=uint_type(16), flags=["a", "b"])
        ff.a = True
        encoded = ff._encode_bits("little")

        recv = FlagsField(type=uint_type(16), flags=["a", "b"])
        recv._decode_bits(encoded, "little")
        assert recv.flag_reads["a"] is True
        assert recv.flag_reads["b"] is False

    def test_single_byte_endian_has_no_effect(self):
        ff = FlagsField(type=uint_type(8), flags=["a"])
        ff.a = True
        assert ff._encode_bits("big") == ff._encode_bits("little")


# ===========================================================================
# Pack / unpack helpers
# ===========================================================================

class TestFlagsFieldPackUnpack:
    def test_pack_all_false_is_zero(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        assert ff._pack({"a": False, "b": False}) == 0

    def test_pack_first_flag_msb(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"])
        assert ff._pack({"a": True, "b": False}) == 128

    def test_pack_lsb_first_first_flag(self):
        ff = FlagsField(type=uint_type(8), flags=["a", "b"], lsb_first=True)
        assert ff._pack({"a": True, "b": False}) == 1

    def test_unpack_round_trips_pack(self):
        ff = FlagsField(type=uint_type(8), flags=["armed", "locked", "error"])
        original = {"armed": True, "locked": False, "error": True}
        packed   = ff._pack(original)
        result   = ff._unpack(packed)
        assert result == original


# ===========================================================================
# Display
# ===========================================================================

class TestFlagsFieldDisplay:
    def test_repr_contains_name(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"], name="status")
        assert "status" in repr(ff)

    def test_repr_contains_type(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"], name="status")
        assert "uint8" in repr(ff)

    def test_repr_flag_true_shown(self):
        ff = FlagsField(type=uint_type(8), flags=["armed"])
        ff.armed = True
        assert "armed=✓" in repr(ff)

    def test_repr_flag_false_shown(self):
        ff = FlagsField(type=uint_type(8), flags=["locked"])
        assert "locked=✗" in repr(ff)

    def test_str_contains_name(self):
        ff = FlagsField(type=uint_type(8), flags=["a"], name="ctrl")
        assert "ctrl" in str(ff)