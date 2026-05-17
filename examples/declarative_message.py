"""
declarative_message.py
======================
Demonstrates defining a Message by subclassing fieldframe.Message.

Fields are declared as class variables -- fieldframe picks up their names
automatically, so you do not need to pass name= explicitly.

Covers
------
- Field          : uint, int, float32, float64, ascii string, utf8 string
- ScaledField    : float stored as a compact unsigned integer, auto-sized
- FlagsField     : named boolean bits packed into a single integer field
- ComputedField  : value derived from sibling fields at encode time
- All set styles : .write, [], .set(), flags by attribute and by item
- All get styles : .read, [], .read_values, .write_values, .flag_reads
- encode / decode round-trip via both bit string and bytes
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
    double_type,
    ascii_type,
    utf8_type,
)

# ---------------------------------------------------------------------------
# ComputedField functions -- defined before the class so they are in scope
# ---------------------------------------------------------------------------


def increase(fields):
    """Auto-incrementing sequence number that wraps at 255."""
    for f in fields:
        if f.name == "seqno":
            return (f.write + 1) % 256
    return 0


def msg_length(fields):
    """Total message length in bytes, excluding the length field itself."""
    return sum(f.length() for f in fields if f.name != "length") // 8


def xor_checksum(fields):
    """XOR of every integer write value except the checksum field itself."""
    acc = 0
    for f in fields:
        if f.name == "checksum":
            continue
        val = getattr(f, "write", None)
        if isinstance(val, int):
            acc ^= val & 0xFF
    return acc & 0xFF


# ---------------------------------------------------------------------------
# Declarative message definition
# ---------------------------------------------------------------------------


class VehicleData(Message):
    """
    A realistic vehicle telemetry frame that exercises every field type.

    Wire layout (big-endian, MSB first):
        unit_id      uint8       ECU identifier
        gear         int8        signed gear position  (-1=reverse, 0=neutral, 1-8)
        fuel_level   uint8       fuel level percent    (0 to 100)
        speed        int16       signed speed cm/s     (-32768 to 32767)
        engine_temp  float32     IEEE 754 temperature  degrees C
        odometer     float64     IEEE 754 total km     double precision
        plate        ascii[6]    6-byte null-padded ASCII number plate
        label        utf8[16]    16-byte null-padded UTF-8 vehicle label
        throttle     scaled/8b   0.0-100.0 % in 0.5 steps (8 bits)
        status       uint8       4 named boolean flags
        seqno        uint8       auto-incrementing sequence number
        len          uint8       frame length in bytes (excl. length field)
        checksum     uint8       XOR checksum of all integer fields
    """

    # -- Integer fields ------------------------------------------------
    unit_id = Field(type=uint_type(8), default=1)  # unsigned ECU id
    gear = Field(type=int_type(8), default=0)  # signed -- reverse is negative
    fuel_level = Field(type=uint_type(8), default=100)  # percent
    speed = Field(type=int_type(16), default=0)  # signed cm/s

    # -- Float fields --------------------------------------------------
    engine_temp = Field(type=single_type(), default=0.0)  # 32-bit IEEE 754 degrees C
    odometer = Field(type=double_type(), default=0.0)  # 64-bit IEEE 754 total km

    # -- String fields -------------------------------------------------
    plate = Field(type=ascii_type(6), default="")  # fixed 6-byte ASCII number plate
    label = Field(type=utf8_type(16), default="")  # fixed 16-byte UTF-8 vehicle label

    # -- Scaled field --------------------------------------------------
    # float stored as a compact uint -- bit width auto-calculated from range
    # 0.0-100.0 % in 0.5 steps -- 8 bits on the wire
    throttle = ScaledField(
        name="throttle",
        min_val=0.0,
        max_val=100.0,
        resolution=0.5,
    )

    # -- Flags field ---------------------------------------------------
    # 4 named booleans packed into one uint8, LSB = first flag
    status = FlagsField(
        type=uint_type(8),
        flags=["engine_on", "handbrake", "doors_locked", "lights_on"],
        lsb_first=True,
    )

    # -- Computed fields -----------------------------------------------
    seqno = ComputedField(type=uint_type(8), compute=increase, default=0)
    len = ComputedField(type=uint_type(8), compute=msg_length, default=0)
    checksum = ComputedField(type=uint_type(8), compute=xor_checksum, default=0)


# ---------------------------------------------------------------------------
# Instantiate
# ---------------------------------------------------------------------------

msg = VehicleData()

# ---------------------------------------------------------------------------
# Setting values -- all three styles work for regular fields
# ---------------------------------------------------------------------------

# 1. Direct .write attribute
msg.gear.write = -1  # reverse
msg.fuel_level.write = 85
msg.engine_temp.write = 92.3
msg.odometer.write = 54231.7

# 2. Item assignment (square bracket)
msg["unit_id"] = 7
msg["speed"] = -250  # reversing
msg["plate"] = "ABC123"
msg["label"] = "delivery-van"
msg["throttle"] = 22.5  # ScaledField -- accepts float
msg["odometer"] = 54231.7

# 3. .set() -- multiple fields at once
msg.set(fuel_level=60, speed=8000, gear=3)

# -- FlagsField set styles -------------------------------------------
msg.status.engine_on = True  # attribute on the FlagsField
msg.status.handbrake = False
msg["status"]["doors_locked"] = True  # item access into the FlagsField
msg["status"]["lights_on"] = True

# ---------------------------------------------------------------------------
# Pretty print before encode -- shows write-side state
# ---------------------------------------------------------------------------

print("=" * 60)
print("BEFORE ENCODE -- write-side state")
print("=" * 60)
print(msg)  # box-drawn table of all fields

# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------

bits = msg.encode()  # bit string -- ComputedFields calculated here
data = msg.encode_bytes()  # bytes, padded to byte boundary

print("\nBit string :", bits)
print("Bytes       :", data)
print("Write vals  :", msg.write_values)  # capture AFTER encode for computed fields

# ---------------------------------------------------------------------------
# Decode round-trip
# ---------------------------------------------------------------------------

msg.decode(bits)  # in-place decode from bit string
msg.decode_bytes(data)  # in-place decode from bytes

print("\nRead vals   :", msg.read_values)

# ---------------------------------------------------------------------------
# Reading values -- all styles
# ---------------------------------------------------------------------------

print("\n--- Individual field reads ---")
print("fuel_level.read          :", msg.fuel_level.read)  # via .read
print("msg['fuel_level'].read   :", msg["fuel_level"].read)  # via item access
print("speed.read               :", msg.speed.read)
print("engine_temp.read         :", msg.engine_temp.read)
print("odometer.read            :", msg.odometer.read)
print("plate.read               :", msg.plate.read)
print("label.read               :", msg.label.read)
print("throttle.read            :", msg.throttle.read)  # logical float
print("throttle.read_raw        :", msg.throttle.read_raw)  # raw wire integer

print("\n--- FlagsField reads ---")
print("flag_reads               :", msg.status.flag_reads)  # full {name: bool} dict
print("status.read (packed)     :", msg.status.read)  # packed integer

print("\n--- ComputedField reads ---")
print("seqno.read               :", msg.seqno.read)
print("len.read              :", msg.len.read)
print("checksum.read            :", msg.checksum.read)

# ---------------------------------------------------------------------------
# Pretty print after decode -- shows both write and read columns populated
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("AFTER DECODE -- both write and read columns")
print("=" * 60)
print(msg)
