"""
declarative_protocol.py
========================
Demonstrates defining a Protocol by subclassing fieldframe.Protocol.

Nested Message classes named Header are picked up automatically.
Any other nested Message subclass that has a _msg_id attribute is registered
as a typed message under that key.

The protocol automatically:
  - Prepends a deep copy of the Header to every registered message
  - Stamps each message's header with its own _msg_id value
  - Routes incoming bitstreams to the correct message type at decode time

Checksum design
---------------
The CRC is the last field inside each message payload. Because ComputedField
receives the full flattened field list of its parent message -- which includes
the injected header fields -- it can XOR every field in the frame in one pass.
This gives whole-frame integrity with no footer required.

Wire layout of every frame:
    [Header] msg_id(8) ecu_id(8) version(4)
    [Payload fields...]
    [crc(8)] -- last field, covers header + all payload fields above it

Covers
------
- Protocol subclassing with key= and name= class keywords
- Header auto-injection
- Five message types covering all field families
- CRC as last ComputedField in each message, covering the full frame
- get_message() -- look up a registered message by name
- encode via the protocol's registered instance (correct pattern)
- decode -- protocol routes by key field automatically
- display() -- pretty print all registered messages
"""

from fieldframe import (
    Message,
    Field,
    FlagsField,
    ScaledField,
    ComputedField,
    uint_type,
    int_type,
    single_type,
    ascii_type,
)
from fieldframe.protocols import Protocol


# ---------------------------------------------------------------------------
# ComputedField functions
# ---------------------------------------------------------------------------


def frame_crc(fields):
    """XOR of every integer write value in the frame except the CRC itself.

    Because this is the last field in the message, and the Header has already
    been injected as the first fields, this sees the complete frame:
        [msg_id, ecu_id, version, ...payload fields..., crc]
    It skips crc and XORs everything else for a true whole-frame check.
    """
    acc = 0
    for f in fields:
        if f.name == "crc":
            continue
        val = getattr(f, "write", None)
        if isinstance(val, int):
            acc ^= val & 0xFF
    return acc & 0xFF


def payload_length(fields):
    """Payload length in bytes, excluding the length and crc fields."""
    return sum(f.length() for f in fields if f.name not in ("length", "crc")) // 8


# ---------------------------------------------------------------------------
# Protocol definition -- declarative subclass style
# ---------------------------------------------------------------------------


class CarProtocol(Protocol, key="msg_id", name="CarProtocol"):
    """
    A multi-message automotive protocol with a shared header.

    Wire layout of every frame:
        [Header] msg_id(8) ecu_id(8) version(4)
        [Payload] -- varies by message type
        [crc(8)] -- last field, XOR of all preceding integer fields

    Messages:
        1  Heartbeat      -- ECU liveness ping
        2  VehicleStatus  -- speed, rpm, fuel and system flags
        3  GpsPosition    -- lat/lon/alt, float fields
        4  WheelCommand   -- sub-byte field, scaled torque, little-endian
        5  DiagnosticLog  -- dense sensor payload with computed length
    """

    # -- Header -- prepended to every message automatically ---------------
    class Header(Message):
        msg_id = Field(type=uint_type(8), default=0)  # routing key
        ecu_id = Field(type=uint_type(8), default=0)  # sending ECU identifier
        version = Field(type=uint_type(4), default=1)  # protocol version

    # -- 1. Heartbeat -----------------------------------------------------
    class Heartbeat(Message):
        """Periodic ECU liveness ping -- sent by every node at 1 Hz."""

        _msg_id = "1"
        unit_id = Field(type=uint_type(8), default=1)
        uptime = Field(type=uint_type(32), default=0)  # seconds since ignition
        vin = Field(type=ascii_type(6), default="")  # 6-char VIN fragment
        state = FlagsField(
            type=uint_type(8),
            flags=["online", "healthy", "busy", "degraded"],
        )
        crc = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

    # -- 2. VehicleStatus -------------------------------------------------
    class VehicleStatus(Message):
        """Live vehicle state -- speed, rpm, fuel level, system flags."""

        _msg_id = "2"
        flags = FlagsField(
            type=uint_type(8),
            flags=["engine_on", "handbrake", "doors_locked", "lights_on"],
        )
        speed = Field(type=uint_type(8), default=0)  # km/h
        rpm = Field(type=uint_type(16), default=0)
        fuel_pct = Field(type=uint_type(8), default=100)  # 0-100 %
        gear = Field(type=int_type(8), default=0)  # signed -- reverse is negative
        crc = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

    # -- 3. GpsPosition ---------------------------------------------------
    class GpsPosition(Message):
        """Raw GPS fix -- float fields for coordinate precision."""

        _msg_id = "3"
        latitude = Field(type=single_type(), default=0.0)  # float32 degrees
        longitude = Field(type=single_type(), default=0.0)  # float32 degrees
        altitude_m = Field(type=uint_type(16), default=0)
        satellites = Field(type=uint_type(8), default=0)
        hdop = Field(type=uint_type(8), default=0)  # x10 fixed-point
        crc = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

    # -- 4. WheelCommand -- little-endian CAN-style frame -----------------
    class WheelCommand(Message, endian="little"):
        """Wheel torque command -- little-endian wire format for CAN."""

        _msg_id = "4"
        wheel_id = Field(type=uint_type(4), default=0)  # sub-byte: 0-3 per corner
        direction = Field(type=int_type(8), default=0)  # signed -- reverse is negative
        torque = ScaledField(  # 0-100 % in 0.5 steps -- 8 bits
            name="torque",
            min_val=0.0,
            max_val=100.0,
            resolution=0.5,
        )
        crc = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

    # -- 5. DiagnosticLog -------------------------------------------------
    class DiagnosticLog(Message):
        """Dense OBD-style sensor payload with a computed frame length."""

        _msg_id = "5"
        timestamp = Field(type=uint_type(32), default=0)
        engine_temp = Field(type=int_type(16), default=0)  # signed, 0.01 degC
        oil_pressure = Field(type=uint_type(16), default=0)  # kPa
        battery_mv = Field(type=uint_type(16), default=0)  # millivolts
        intake_temp = Field(type=int_type(8), default=0)  # signed degC
        throttle_pos = Field(type=uint_type(8), default=0)  # 0-100 %
        brake_press = Field(type=uint_type(8), default=0)  # 0-100 %
        length = ComputedField(type=uint_type(8), compute=payload_length, default=0)
        crc = ComputedField(type=uint_type(8), compute=frame_crc, default=0)


# ---------------------------------------------------------------------------
# Instantiate -- one protocol instance for the whole application
# ---------------------------------------------------------------------------

protocol = CarProtocol()

# ---------------------------------------------------------------------------
# Heartbeat -- encode via the protocol's registered instance
# ---------------------------------------------------------------------------

# IMPORTANT: always encode via protocol.messages[key], not a bare class
# instance -- the registered instance already has the header injected,
# so the crc field sees the full frame including header fields.
hb = protocol.messages["1"]
hb.unit_id.write = 3
hb.uptime.write = 7200  # 2 hours since ignition
hb["vin"] = "1HGCM8"
hb.state.online = True
hb.state.healthy = True
hb.state.busy = False
hb.state.degraded = False

bits = hb.encode()
result = protocol.decode(bits)

# Capture write_values AFTER encode so crc reflects the just-computed value
print("=" * 60)
print("Heartbeat round-trip")
print("=" * 60)
print("Sent   :", hb.write_values)
print("Decoded:", result)

# ---------------------------------------------------------------------------
# GpsPosition
# ---------------------------------------------------------------------------

gps = protocol.messages["3"]
gps.latitude.write = -33.8688  # Sydney
gps.longitude.write = 151.2093
gps["altitude_m"] = 58
gps.set(satellites=11, hdop=8)

bits = gps.encode()
result = protocol.decode(bits)

print("\n" + "=" * 60)
print("GpsPosition round-trip")
print("=" * 60)
print("Sent   :", gps.write_values)
print("Decoded:", result)

# ---------------------------------------------------------------------------
# WheelCommand -- little-endian
# ---------------------------------------------------------------------------

wc = protocol.messages["4"]
wc.wheel_id.write = 2  # rear-right
wc.direction.write = -1  # signed -- braking/reverse
wc["torque"] = 45.0  # ScaledField via item access

bits = wc.encode()
result = protocol.decode(bits)

print("\n" + "=" * 60)
print("WheelCommand round-trip (little-endian)")
print("=" * 60)
print("Sent   :", wc.write_values)
print("Decoded:", result)

# ---------------------------------------------------------------------------
# DiagnosticLog -- get_message by name, then encode
# ---------------------------------------------------------------------------

dl = protocol.get_message("DiagnosticLog")  # look up by message name
dl["timestamp"] = 1_700_000_000
dl["engine_temp"] = 9230  # 92.30 degC in 0.01 degC units
dl["oil_pressure"] = 280  # kPa
dl["battery_mv"] = 12650  # 12.65 V in millivolts
dl.set(intake_temp=35, throttle_pos=42, brake_press=0)

bits = dl.encode()
result = protocol.decode(bits)

print("\n" + "=" * 60)
print("DiagnosticLog round-trip")
print("=" * 60)
print("Sent   :", dl.write_values)
print("Decoded:", result)

# ---------------------------------------------------------------------------
# Display -- pretty print all registered messages
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("Protocol overview")
print("=" * 60)
protocol.display()
