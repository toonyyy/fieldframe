"""
Tests for fieldframe.core — Message class.
"""

import pytest
from fieldframe.core import Message
from fieldframe.fields.field import Field
from fieldframe.fields.flags import FlagsField
from fieldframe.fields.compute import ComputedField
from fieldframe.types.int import uint_type, int_type


# ---------------------------------------------------------------------------
# Module-level Message subclasses (declarative style)
# ---------------------------------------------------------------------------


class SpeedMsg(Message):
    speed = Field(type=uint_type(8), default=0)


class GuidanceMsg(Message):
    speed = Field(type=uint_type(8), default=0)
    heading = Field(type=int_type(16), default=0)


class LittleMsg(Message, endian="little"):
    value = Field(type=uint_type(16), default=0)


class ReversedMsg(Message, reversed=True):
    byte = Field(type=uint_type(8), default=0)


class FlagsMsg(Message):
    status = FlagsField(type=uint_type(8), flags=["armed", "locked", "error", "ready"])


def _xor_checksum(fields):
    acc = 0
    for f in fields:
        if hasattr(f, "write") and hasattr(f, "name") and f.name != "checksum":
            acc ^= f.write or 0
    return acc & 0xFF


class ChecksumMsg(Message):
    payload = Field(type=uint_type(8), default=0)
    checksum = ComputedField(type=uint_type(8), compute=_xor_checksum)


class HeaderMsg(Message):
    version = Field(type=uint_type(4), default=1)
    msg_id = Field(type=uint_type(12), default=0)


class NestedMsg(Message):
    header = HeaderMsg()
    altitude = Field(type=uint_type(16), default=0)


# ===========================================================================
# Construction
# ===========================================================================


class TestMessageConstruction:
    # --- Declarative style ---

    def test_declarative_name_defaults_to_class_name(self):
        msg = SpeedMsg()
        assert msg.name == "SpeedMsg"

    def test_declarative_fields_populated(self):
        msg = SpeedMsg()
        assert len(msg.fields) == 1
        assert msg.fields[0].name == "speed"

    def test_declarative_each_instance_gets_own_fields(self):
        a = SpeedMsg()
        b = SpeedMsg()
        a.speed.write = 99
        assert b.speed.write == 0  # independent deepcopy

    def test_declarative_endian_default_big(self):
        assert SpeedMsg().endian == "big"

    def test_declarative_endian_little(self):
        assert LittleMsg().endian == "little"

    def test_declarative_reversed_default_false(self):
        assert SpeedMsg().reversal is False

    def test_declarative_reversed_true(self):
        assert ReversedMsg().reversal is True

    # --- Direct style ---

    def test_direct_explicit_name(self):
        msg = Message("Packet", [Field(name="x", type=uint_type(8), default=0)])
        assert msg.name == "Packet"

    def test_direct_fields_stored(self):
        f = Field(name="x", type=uint_type(8), default=0)
        msg = Message("P", [f])
        assert len(msg.fields) == 1

    def test_direct_unnamed_field_raises(self):
        with pytest.raises(ValueError, match="name"):
            Message("P", [Field(type=uint_type(8), default=0)])

    def test_direct_endian_big_default(self):
        msg = Message("P", [Field(name="x", type=uint_type(8), default=0)])
        assert msg.endian == "big"

    def test_direct_endian_little(self):
        msg = Message(
            "P", [Field(name="x", type=uint_type(8), default=0)], endian="little"
        )
        assert msg.endian == "little"

    def test_invalid_endian_raises(self):
        with pytest.raises(ValueError, match="endian"):
            Message(
                "P", [Field(name="x", type=uint_type(8), default=0)], endian="middle"
            )

    def test_direct_empty_fields_ok(self):
        msg = Message("Empty", [])
        assert msg.fields == []

    def test_name_override_on_declarative(self):
        msg = SpeedMsg(name="CustomName")
        assert msg.name == "CustomName"


# ===========================================================================
# length()
# ===========================================================================


class TestMessageLength:
    def test_single_8bit_field(self):
        assert SpeedMsg().length() == 8

    def test_two_fields(self):
        assert GuidanceMsg().length() == 24  # 8 + 16

    def test_empty_message(self):
        assert Message("E", []).length() == 0

    def test_nested_message_length(self):
        # HeaderMsg = 4+12=16 bits, altitude=16 bits, total=32
        assert NestedMsg().length() == 32

    def test_flags_field_length(self):
        assert FlagsMsg().length() == 8

    def test_direct_style_length(self):
        msg = Message(
            "P",
            [
                Field(name="a", type=uint_type(8), default=0),
                Field(name="b", type=uint_type(16), default=0),
            ],
        )
        assert msg.length() == 24


# ===========================================================================
# encode / decode round trips
# ===========================================================================


class TestMessageEncodeDecode:
    def test_single_field_round_trip(self):
        msg = SpeedMsg()
        msg.speed.write = 200
        bits = msg.encode()
        assert bits == "11001000"
        result = msg.decode(bits)
        assert result["speed"] == 200

    def test_multiple_field_round_trip(self):
        msg = GuidanceMsg()
        msg.speed.write = 120
        msg.heading.write = -500
        bits = msg.encode()
        assert len(bits) == 24
        result = msg.decode(bits)
        assert result["speed"] == 120
        assert result["heading"] == -500

    def test_encode_returns_only_01_chars(self):
        msg = GuidanceMsg()
        bits = msg.encode()
        assert set(bits) <= {"0", "1"}

    def test_encode_length_equals_message_length(self):
        msg = GuidanceMsg()
        assert len(msg.encode()) == msg.length()

    def test_zero_default_encodes_to_all_zeros(self):
        msg = SpeedMsg()
        assert msg.encode() == "0" * 8

    def test_decode_populates_read(self):
        msg = SpeedMsg()
        msg.decode("11001000")
        assert msg.speed.read == 200

    def test_decode_returns_dict(self):
        msg = SpeedMsg()
        result = msg.decode("11001000")
        assert isinstance(result, dict)
        assert "speed" in result

    @pytest.mark.parametrize("value", [0, 1, 127, 128, 255])
    def test_parametrized_round_trip(self, value):
        msg = SpeedMsg()
        msg.speed.write = value
        assert msg.decode(msg.encode())["speed"] == value


# ===========================================================================
# Little-endian and reversed modes
# ===========================================================================


class TestMessageEndianAndReversal:
    def test_little_endian_differs_from_big_for_multibyte(self):
        big = GuidanceMsg()
        big.heading.write = 256
        little = GuidanceMsg(endian="little")
        little.heading.write = 256
        assert big.encode() != little.encode()

    def test_little_endian_round_trip(self):
        msg = LittleMsg()
        msg.value.write = 1000
        result = msg.decode(msg.encode())
        assert result["value"] == 1000

    def test_reversed_round_trip(self):
        msg = ReversedMsg()
        msg.byte.write = 99
        bits = msg.encode()
        result = msg.decode(bits)
        assert result["byte"] == 99

    def test_reversed_bit_string_differs_from_normal(self):
        normal = SpeedMsg()
        reversed_ = ReversedMsg()
        normal.speed.write = 99
        reversed_.byte.write = 99
        assert normal.encode() != reversed_.encode()


# ===========================================================================
# Nested sub-messages
# ===========================================================================


class TestMessageNested:
    def test_nested_length(self):
        assert NestedMsg().length() == 32  # 16 (header) + 16 (altitude)

    def test_nested_encode_length(self):
        msg = NestedMsg()
        assert len(msg.encode()) == 32

    def test_nested_round_trip(self):
        msg = NestedMsg()
        msg.header.version.write = 2
        msg.header.msg_id.write = 7
        msg.altitude.write = 1500
        bits = msg.encode()
        result = msg.decode(bits)
        assert result["header"]["version"] == 2
        assert result["header"]["msg_id"] == 7
        assert result["altitude"] == 1500

    def test_nested_read_values_structure(self):
        msg = NestedMsg()
        msg.decode(msg.encode())
        rv = msg.read_values
        assert "header" in rv
        assert "altitude" in rv
        assert isinstance(rv["header"], dict)


# ===========================================================================
# ComputedField inside Message
# ===========================================================================


class TestMessageComputedField:
    def test_computed_field_called_on_encode(self):
        msg = ChecksumMsg()
        msg.payload.write = 0xAB
        bits = msg.encode()
        # checksum = 0xAB XOR 0 (checksum itself skipped) = 0xAB
        assert len(bits) == 16

    def test_computed_field_round_trip(self):
        msg = ChecksumMsg()
        msg.payload.write = 0x42
        bits = msg.encode()
        result = msg.decode(bits)
        # checksum on decode reads the raw wire value, not recomputed
        assert result["payload"] == 0x42
        assert result["checksum"] == 0x42  # xor of payload only

    def test_computed_field_write_updated_after_encode(self):
        msg = ChecksumMsg()
        msg.payload.write = 0xFF
        msg.encode()
        assert msg.checksum.write == 0xFF


# ===========================================================================
# FlagsField inside Message
# ===========================================================================


class TestMessageFlagsField:
    def test_flags_round_trip(self):
        msg = FlagsMsg()
        msg.status.armed = True
        msg.status.ready = True
        bits = msg.encode()
        result = msg.decode(bits)
        # read values contains packed int
        assert result["status"] == msg.status.write

    def test_flags_encode_length(self):
        msg = FlagsMsg()
        assert len(msg.encode()) == 8


# ===========================================================================
# Bytes API — encode_bytes / decode_bytes / from_bits / from_bytes
# ===========================================================================


class TestMessageBytesAPI:
    def test_encode_bytes_returns_bytes(self):
        msg = SpeedMsg()
        msg.speed.write = 200
        assert isinstance(msg.encode_bytes(), bytes)

    def test_encode_decode_bytes_round_trip(self):
        msg = SpeedMsg()
        msg.speed.write = 200
        data = msg.encode_bytes()
        result = msg.decode_bytes(data)
        assert result["speed"] == 200

    def test_encode_decode_bytes_multi_field(self):
        msg = GuidanceMsg()
        msg.speed.write = 120
        msg.heading.write = -100
        result = msg.decode_bytes(msg.encode_bytes())
        assert result["speed"] == 120
        assert result["heading"] == -100

    def test_from_bits_round_trip(self):
        msg = SpeedMsg()
        msg.speed.write = 77
        bits = msg.encode()
        loaded = SpeedMsg.from_bits(bits)
        assert loaded.speed.read == 77

    def test_from_bits_requires_subclass(self):
        with pytest.raises(TypeError, match="subclass"):
            Message.from_bits("00000000")

    def test_from_bytes_round_trip(self):
        msg = SpeedMsg()
        msg.speed.write = 33
        loaded = SpeedMsg.from_bytes(msg.encode_bytes())
        assert loaded.speed.read == 33

    def test_from_bytes_requires_subclass(self):
        with pytest.raises(TypeError, match="subclass"):
            Message.from_bytes(b"\x00")


# ===========================================================================
# Padding helpers
# ===========================================================================


class TestMessagePadding:
    def test_byte_aligned_no_padding(self):
        msg = SpeedMsg()  # 8 bits
        assert msg._pad_count() == 0

    def test_non_aligned_pad_count(self):
        # 4+12 = 16 bits → aligned, 0 pad
        hdr = HeaderMsg()
        assert hdr._pad_count() == 0

    def test_3bit_field_pad_count(self):
        msg = Message("P", [Field(name="x", type=uint_type(3), default=0)])
        assert msg._pad_count() == 5  # 3 bits → needs 5 to reach 8

    def test_apply_padding_big_endian(self):
        msg = Message("P", [Field(name="x", type=uint_type(3), default=0)])
        padded = msg._apply_padding("101")
        assert padded == "101" + "0" * 5

    def test_apply_padding_little_endian(self):
        msg = Message(
            "P", [Field(name="x", type=uint_type(3), default=0)], endian="little"
        )
        padded = msg._apply_padding("101")
        assert padded == "0" * 5 + "101"

    def test_strip_padding_inverts_apply(self):
        msg = Message("P", [Field(name="x", type=uint_type(3), default=0)])
        original = "101"
        assert msg._strip_padding(msg._apply_padding(original)) == original


# ===========================================================================
# Field access — __getattr__ / __getitem__ / __setitem__ / set()
# ===========================================================================


class TestMessageFieldAccess:
    def test_getattr_returns_field(self):
        msg = SpeedMsg()
        field = msg.speed
        assert field.name == "speed"

    def test_getattr_unknown_raises_attribute_error(self):
        msg = SpeedMsg()
        with pytest.raises(AttributeError):
            _ = msg.nonexistent

    def test_getitem_returns_field(self):
        msg = SpeedMsg()
        assert msg["speed"].name == "speed"

    def test_getitem_unknown_raises_key_error(self):
        msg = SpeedMsg()
        with pytest.raises(KeyError):
            _ = msg["nonexistent"]

    def test_setitem_updates_write(self):
        msg = SpeedMsg()
        msg["speed"] = 42
        assert msg.speed.write == 42

    def test_setitem_unknown_raises_key_error(self):
        msg = SpeedMsg()
        with pytest.raises(KeyError):
            msg["nonexistent"] = 0

    def test_set_method_updates_write(self):
        msg = GuidanceMsg()
        msg.set(speed=100, heading=-200)
        assert msg.speed.write == 100
        assert msg.heading.write == -200

    def test_set_unknown_field_raises_key_error(self):
        msg = SpeedMsg()
        with pytest.raises(KeyError):
            msg.set(nonexistent=0)

    def test_set_sub_message_raises_type_error(self):
        msg = NestedMsg()
        with pytest.raises(TypeError, match="sub-message"):
            msg.set(header=0)

    def test_set_out_of_range_raises_value_error(self):
        msg = SpeedMsg()
        with pytest.raises(ValueError):
            msg.set(speed=999)


# ===========================================================================
# Dynamic field manipulation — add_field / remove_field
# ===========================================================================


class TestMessageDynamicFields:
    def test_add_field_appends_by_default(self):
        msg = SpeedMsg()
        f = Field(name="extra", type=uint_type(8), default=0)
        msg.add_field(f)
        assert msg.fields[-1].name == "extra"
        assert msg.length() == 16

    def test_add_field_at_position_zero(self):
        msg = SpeedMsg()
        f = Field(name="first", type=uint_type(8), default=0)
        msg.add_field(f, position=0)
        assert msg.fields[0].name == "first"

    def test_add_field_position_out_of_bounds_raises(self):
        msg = SpeedMsg()
        f = Field(name="x", type=uint_type(8), default=0)
        with pytest.raises(IndexError):
            msg.add_field(f, position=99)

    def test_remove_field_removes_by_position(self):
        msg = GuidanceMsg()
        msg.remove_field(0)
        assert len(msg.fields) == 1
        assert msg.fields[0].name == "heading"

    def test_remove_field_out_of_bounds_raises(self):
        msg = SpeedMsg()
        with pytest.raises(IndexError):
            msg.remove_field(5)

    def test_add_then_remove_round_trip(self):
        msg = SpeedMsg()
        original_len = len(msg.fields)
        f = Field(name="tmp", type=uint_type(8), default=0)
        msg.add_field(f)
        msg.remove_field(len(msg.fields) - 1)
        assert len(msg.fields) == original_len


# ===========================================================================
# write_values / read_values properties
# ===========================================================================


class TestMessageValueProperties:
    def test_write_values_contains_all_fields(self):
        msg = GuidanceMsg()
        wv = msg.write_values
        assert "speed" in wv
        assert "heading" in wv

    def test_write_values_reflect_staged_values(self):
        msg = GuidanceMsg()
        msg.speed.write = 77
        msg.heading.write = -10
        wv = msg.write_values
        assert wv["speed"] == 77
        assert wv["heading"] == -10

    def test_read_values_none_before_decode(self):
        msg = SpeedMsg()
        assert msg.read_values["speed"] is None

    def test_read_values_populated_after_decode(self):
        msg = SpeedMsg()
        msg.speed.write = 55
        msg.decode(msg.encode())
        assert msg.read_values["speed"] == 55

    def test_nested_write_values_structure(self):
        msg = NestedMsg()
        wv = msg.write_values
        assert isinstance(wv["header"], dict)
        assert "version" in wv["header"]

    def test_nested_read_values_structure(self):
        msg = NestedMsg()
        msg.decode(msg.encode())
        rv = msg.read_values
        assert isinstance(rv["header"], dict)


# ===========================================================================
# Display — __repr__ / __str__
# ===========================================================================


class TestMessageDisplay:
    def test_repr_contains_name(self):
        msg = SpeedMsg()
        assert "SpeedMsg" in repr(msg)

    def test_repr_contains_endian(self):
        msg = SpeedMsg()
        assert "big-endian" in repr(msg)

    def test_repr_contains_bits(self):
        msg = SpeedMsg()
        assert "8 bits" in repr(msg)

    def test_repr_contains_field_count(self):
        msg = GuidanceMsg()
        assert "2 fields" in repr(msg)

    def test_str_contains_name(self):
        msg = SpeedMsg()
        assert "SpeedMsg" in str(msg)

    def test_str_contains_field_names(self):
        msg = GuidanceMsg()
        s = str(msg)
        assert "speed" in s
        assert "heading" in s

    def test_str_nested_contains_sub_message(self):
        msg = NestedMsg()
        s = str(msg)
        assert "header" in s
        assert "altitude" in s
