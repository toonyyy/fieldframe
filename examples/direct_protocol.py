"""
direct_protocol.py
==================
Demonstrates defining a Protocol by passing message instances directly to
the Protocol constructor -- no subclassing required.

Every message and the header are constructed as Message("name", [...])
instances and passed in. The protocol still automatically prepends the header
and stamps each message's key field value.

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
- Protocol direct instantiation with name=, header=, key=, messages=
- Header as a plain Message instance
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
# Build all message instances directly
# ---------------------------------------------------------------------------

# -- Header ---------------------------------------------------------------
header = Message(
    "Header",
    [
        Field(name="msg_id", type=uint_type(8), default=0),  # routing key
        Field(name="ecu_id", type=uint_type(8), default=0),  # sending ECU identifier
        Field(name="version", type=uint_type(4), default=1),  # protocol version
    ],
)

# -- 1. Heartbeat ---------------------------------------------------------
heartbeat = Message(
    "Heartbeat",
    [
        Field(name="unit_id", type=uint_type(8), default=1),
        Field(name="uptime", type=uint_type(32), default=0),  # seconds since ignition
        Field(name="vin", type=ascii_type(6), default=""),  # 6-char VIN fragment
        FlagsField(
            name="state",
            type=uint_type(8),
            flags=["online", "healthy", "busy", "degraded"],
        ),
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ],
)

# -- 2. VehicleStatus -----------------------------------------------------
vehicle_status = Message(
    "VehicleStatus",
    [
        FlagsField(
            name="flags",
            type=uint_type(8),
            flags=["engine_on", "handbrake", "doors_locked", "lights_on"],
        ),
        Field(name="speed", type=uint_type(8), default=0),  # km/h
        Field(name="rpm", type=uint_type(16), default=0),
        Field(name="fuel_pct", type=uint_type(8), default=100),  # 0-100 %
        Field(
            name="gear", type=int_type(8), default=0
        ),  # signed -- reverse is negative
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ],
)

# -- 3. GpsPosition -------------------------------------------------------
gps_position = Message(
    "GpsPosition",
    [
        Field(name="latitude", type=single_type(), default=0.0),  # float32 degrees
        Field(name="longitude", type=single_type(), default=0.0),  # float32 degrees
        Field(name="altitude_m", type=uint_type(16), default=0),
        Field(name="satellites", type=uint_type(8), default=0),
        Field(name="hdop", type=uint_type(8), default=0),  # x10 fixed-point
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ],
)

# -- 4. WheelCommand -- little-endian CAN-style frame ---------------------
wheel_command = Message(
    "WheelCommand",
    [
        Field(
            name="wheel_id", type=uint_type(4), default=0
        ),  # sub-byte: 0-3 per corner
        Field(
            name="direction", type=int_type(8), default=0
        ),  # signed -- reverse is negative
        ScaledField(name="torque", min_val=0.0, max_val=100.0, resolution=0.5),
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ],
    endian="little",
)

# -- 5. DiagnosticLog -----------------------------------------------------
diagnostic_log = Message(
    "DiagnosticLog",
    [
        Field(name="timestamp", type=uint_type(32), default=0),
        Field(name="engine_temp", type=int_type(16), default=0),  # signed, 0.01 degC
        Field(name="oil_pressure", type=uint_type(16), default=0),  # kPa
        Field(name="battery_mv", type=uint_type(16), default=0),  # millivolts
        Field(name="intake_temp", type=int_type(8), default=0),  # signed degC
        Field(name="throttle_pos", type=uint_type(8), default=0),  # 0-100 %
        Field(name="brake_press", type=uint_type(8), default=0),  # 0-100 %
        ComputedField(
            name="length", type=uint_type(8), compute=payload_length, default=0
        ),
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ],
)

# ---------------------------------------------------------------------------
# Instantiate the protocol directly
# ---------------------------------------------------------------------------

protocol = Protocol(
    name="CarProtocol",
    header=header,
    key="msg_id",
    messages={
        "1": heartbeat,
        "2": vehicle_status,
        "3": gps_position,
        "4": wheel_command,
        "5": diagnostic_log,
    },
)

# ---------------------------------------------------------------------------
# Heartbeat -- encode via the protocol's registered instance
# ---------------------------------------------------------------------------

# IMPORTANT: always encode via protocol.messages[key], not a bare instance
# -- the registered instance already has the header injected, so the crc
# field sees the full frame including header fields.
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

dl = protocol.get_message("DiagnosticLog")
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
