"""
Tests for fieldframe.protocols — Protocol class.
"""

import pytest
from fieldframe.core import Message
from fieldframe.protocols import Protocol
from fieldframe.fields.field import Field
from fieldframe.fields.flags import FlagsField
from fieldframe.types.int import uint_type


# ---------------------------------------------------------------------------
# Reusable helpers
# ---------------------------------------------------------------------------

def _make_header(name="Header"):
    return Message(name, [Field(name="msg_id", type=uint_type(8), default=0)])


def _make_proto(name="TestProto", with_footer=False):
    """Build a simple two-message protocol via direct instantiation."""
    header  = _make_header()
    tel     = Message("Telemetry", [Field(name="altitude", type=uint_type(16), default=0)])
    cmd     = Message("Command",   [Field(name="command",  type=uint_type(8),  default=0)])
    kwargs  = dict(name=name, header=header, key="msg_id", messages={"1": tel, "2": cmd})
    if with_footer:
        footer = Message("Footer", [Field(name="crc", type=uint_type(8), default=0)])
        kwargs["footer"] = footer
    return Protocol(**kwargs)


def _encode_telemetry(proto, altitude=0):
    """Encode the telemetry message with a given altitude."""
    msg = proto.messages["1"]
    msg.altitude.write = altitude
    return msg.encode()


# ---------------------------------------------------------------------------
# Declarative Protocol subclass used across tests
# ---------------------------------------------------------------------------

class MyProto(Protocol, key="msg_id", name="MyProto"):

    class Header(Message):
        msg_id = Field(type=uint_type(8), default=0)

    class TelemetryMsg(Message):
        _msg_id  = 1
        altitude = Field(type=uint_type(16), default=0)

    class CommandMsg(Message):
        _msg_id = 2
        command = Field(type=uint_type(8), default=0)


# ===========================================================================
# Declarative subclass style
# ===========================================================================

class TestProtocolDeclarativeStyle:
    def test_name_from_class_keyword(self):
        proto = MyProto()
        assert proto.name == "MyProto"

    def test_key_from_class_keyword(self):
        proto = MyProto()
        assert proto.key == "msg_id"

    def test_messages_registered_from_msg_id(self):
        proto = MyProto()
        assert "1" in proto.messages
        assert "2" in proto.messages

    def test_header_instantiated(self):
        proto = MyProto()
        assert isinstance(proto.header, Message)
        assert "msg_id" in [f.name for f in proto.header.fields]

    def test_each_instance_has_independent_messages(self):
        p1 = MyProto()
        p2 = MyProto()
        p1.messages["1"].altitude.write = 999
        assert p2.messages["1"].altitude.write == 0

    def test_key_value_stamped_into_telemetry_header(self):
        proto = MyProto()
        tel = proto.messages["1"]
        # The embedded header's msg_id should be 1
        assert tel["Header"].msg_id.write == 1

    def test_key_value_stamped_into_command_header(self):
        proto = MyProto()
        cmd = proto.messages["2"]
        assert cmd["Header"].msg_id.write == 2


# ===========================================================================
# Direct instantiation style
# ===========================================================================

class TestProtocolDirectInstantiation:
    def test_name_stored(self):
        proto = _make_proto("DirectProto")
        assert proto.name == "DirectProto"

    def test_key_stored(self):
        proto = _make_proto()
        assert proto.key == "msg_id"

    def test_messages_stored(self):
        proto = _make_proto()
        assert "1" in proto.messages
        assert "2" in proto.messages

    def test_header_prepended_to_each_message(self):
        proto = _make_proto()
        for _, msg in proto.messages.items():
            # First field should be the embedded header
            assert msg.fields[0].name == "Header"

    def test_empty_messages_dict_ok(self):
        header = _make_header()
        proto  = Protocol(name="P", header=header, key="msg_id", messages={})
        assert proto.messages == {}

    def test_footer_appended_to_each_message(self):
        proto = _make_proto(with_footer=True)
        for _, msg in proto.messages.items():
            assert msg.fields[-1].name == "Footer"

    def test_footer_none_by_default(self):
        proto = _make_proto()
        assert proto.footer is None

    def test_key_values_stamped_correctly(self):
        proto = _make_proto()
        tel = proto.messages["1"]
        cmd = proto.messages["2"]
        assert tel["Header"].msg_id.write == 1
        assert cmd["Header"].msg_id.write == 2


# ===========================================================================
# Header / footer / key validation
# ===========================================================================

class TestProtocolHeaderFooterKeyValidation:
    def test_non_message_header_raises_type_error(self):
        with pytest.raises(TypeError, match="Message"):
            Protocol(name="P", header="not_a_message", key="x", messages={})

    def test_none_header_raises_type_error(self):
        with pytest.raises(TypeError):
            Protocol(name="P", header=None, key="x", messages={})

    def test_non_message_footer_raises_type_error(self):
        header = _make_header()
        with pytest.raises(TypeError, match="Message"):
            Protocol(name="P", header=header, key="msg_id", messages={}, footer="bad")

    def test_invalid_key_raises_value_error(self):
        header = _make_header()
        with pytest.raises(ValueError, match="valid key"):
            Protocol(name="P", header=header, key="nonexistent", messages={})

    def test_header_reassignment_raises_attribute_error(self):
        proto = _make_proto()
        with pytest.raises(AttributeError, match="initialisation"):
            proto.header = _make_header()

    def test_footer_reassignment_raises_attribute_error(self):
        proto = _make_proto()
        with pytest.raises(AttributeError, match="initialisation"):
            proto.footer = None


# ===========================================================================
# add_message / remove_message / get_message
# ===========================================================================

class TestProtocolMessageRegistry:
    def test_add_message(self):
        proto = _make_proto()
        new_msg = Message("Status", [Field(name="code", type=uint_type(8), default=0)])
        proto.add_message("3", new_msg)
        assert "3" in proto.messages

    def test_add_duplicate_raises_value_error(self):
        proto = _make_proto()
        with pytest.raises(ValueError, match="already in protocol"):
            proto.add_message("1", Message("X", [Field(name="x", type=uint_type(8), default=0)]))

    def test_remove_message(self):
        proto = _make_proto()
        proto.remove_message("2")
        assert "2" not in proto.messages

    def test_remove_nonexistent_raises_value_error(self):
        proto = _make_proto()
        with pytest.raises(ValueError, match="not in protocol"):
            proto.remove_message("99")

    def test_get_message_by_name(self):
        proto = _make_proto()
        msg = proto.get_message("Telemetry")
        assert msg.name == "Telemetry"

    def test_get_message_command(self):
        proto = _make_proto()
        msg = proto.get_message("Command")
        assert msg.name == "Command"

    def test_get_message_unknown_raises_value_error(self):
        proto = _make_proto()
        with pytest.raises(ValueError, match="not defined"):
            proto.get_message("Nonexistent")


# ===========================================================================
# decode
# ===========================================================================

class TestProtocolDecode:
    def test_decode_telemetry_message(self):
        proto = _make_proto()
        bits  = _encode_telemetry(proto, altitude=300)
        result = proto.decode(bits)
        assert result["altitude"] == 300

    def test_decode_telemetry_header_key_value(self):
        proto = _make_proto()
        bits  = _encode_telemetry(proto, altitude=0)
        result = proto.decode(bits)
        assert result["Header"]["msg_id"] == 1

    def test_decode_command_message(self):
        proto = _make_proto()
        cmd = proto.messages["2"]
        cmd.command.write = 7
        bits   = cmd.encode()
        result = proto.decode(bits)
        assert result["command"] == 7

    def test_decode_command_header_key_value(self):
        proto = _make_proto()
        cmd = proto.messages["2"]
        cmd.command.write = 0
        result = proto.decode(cmd.encode())
        assert result["Header"]["msg_id"] == 2

    @pytest.mark.parametrize("altitude", [0, 1, 300, 1000, 65535])
    def test_decode_various_altitudes(self, altitude):
        proto = _make_proto()
        bits  = _encode_telemetry(proto, altitude=altitude)
        assert proto.decode(bits)["altitude"] == altitude

    def test_decode_unknown_key_raises_key_error(self):
        proto = _make_proto()
        # Manually craft a bit string with msg_id=99 (not registered)
        header_bits = format(99, "08b")       # "01100011"
        payload     = "0" * 16                 # altitude placeholder
        with pytest.raises(KeyError):
            proto.decode(header_bits + payload)

    def test_decode_with_footer(self):
        proto = _make_proto(with_footer=True)
        msg   = proto.messages["1"]
        msg.altitude.write = 500
        bits   = msg.encode()
        result = proto.decode(bits)
        assert result["altitude"] == 500

    def test_declarative_proto_decode_round_trip(self):
        proto = MyProto()
        tel = proto.messages["1"]
        tel.altitude.write = 1234
        bits   = tel.encode()
        result = proto.decode(bits)
        assert result["altitude"] == 1234

    def test_decode_result_contains_header_and_payload(self):
        proto  = _make_proto()
        bits   = _encode_telemetry(proto, altitude=42)
        result = proto.decode(bits)
        assert "Header"   in result
        assert "altitude" in result


# ===========================================================================
# display
# ===========================================================================

class TestProtocolDisplay:
    def test_display_runs_without_error(self, capsys):
        proto = _make_proto()
        proto.display()
        captured = capsys.readouterr()
        assert captured.out != ""

    def test_display_contains_protocol_name(self, capsys):
        proto = _make_proto("SmokeProto")
        proto.display()
        assert "SmokeProto" in capsys.readouterr().out

    def test_display_contains_message_names(self, capsys):
        proto = _make_proto()
        proto.display()
        out = capsys.readouterr().out
        assert "Telemetry" in out
        assert "Command"   in out