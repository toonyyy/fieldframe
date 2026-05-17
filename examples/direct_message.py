"""
direct_message.py
=================
Demonstrates defining a Message by passing a field list directly to the
Message constructor -- no subclassing required.

Every field must be given an explicit name= because there is no class body
for fieldframe to read the attribute name from. Everything else -- encoding,
decoding, validation, pretty printing -- is identical to the declarative style.

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
    Message, Field, FlagsField, ScaledField, ComputedField,
    uint_type, int_type, single_type, double_type, ascii_type, utf8_type,
)

# ---------------------------------------------------------------------------
# ComputedField functions
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
# Direct instantiation -- field list passed to constructor
# ---------------------------------------------------------------------------

msg = Message("VehicleData", [

    # -- Integer fields ------------------------------------------------
    Field(name="unit_id",    type=uint_type(8),  default=1),   # unsigned ECU id
    Field(name="gear",       type=int_type(8),   default=0),   # signed -- reverse is negative
    Field(name="fuel_level", type=uint_type(8),  default=100), # percent
    Field(name="speed",      type=int_type(16),  default=0),   # signed cm/s

    # -- Float fields --------------------------------------------------
    Field(name="engine_temp", type=single_type(), default=0.0), # 32-bit IEEE 754 degrees C
    Field(name="odometer",    type=double_type(), default=0.0), # 64-bit IEEE 754 total km

    # -- String fields -------------------------------------------------
    Field(name="plate", type=ascii_type(6),  default=""),  # fixed 6-byte ASCII number plate
    Field(name="label", type=utf8_type(16),  default=""),  # fixed 16-byte UTF-8 vehicle label

    # -- Scaled field --------------------------------------------------
    # float stored as compact uint -- bit width auto-calculated from range
    # 0.0-100.0 % in 0.5 steps -- 8 bits on the wire
    ScaledField(name="throttle", min_val=0.0, max_val=100.0, resolution=0.5),

    # -- Flags field ---------------------------------------------------
    # 4 named booleans packed into one uint8, LSB = first flag
    FlagsField(
        name="status",
        type=uint_type(8),
        flags=["engine_on", "handbrake", "doors_locked", "lights_on"],
        lsb_first=True,
    ),

    # -- Computed fields -----------------------------------------------
    ComputedField(name="seqno",    type=uint_type(8), compute=increase,     default=0),
    ComputedField(name="len",   type=uint_type(8), compute=msg_length,   default=0),
    ComputedField(name="checksum", type=uint_type(8), compute=xor_checksum, default=0),
])

# ---------------------------------------------------------------------------
# Setting values -- all three styles work identically to the declarative style
# ---------------------------------------------------------------------------

# 1. Direct .write attribute
msg.gear.write        = -1       # reverse
msg.fuel_level.write  = 85
msg.engine_temp.write = 92.3
msg.odometer.write    = 54231.7

# 2. Item assignment (square bracket)
msg['unit_id']  = 7
msg['speed']    = -250           # reversing
msg['plate']    = "ABC123"
msg['label']    = "delivery-van"
msg['throttle'] = 22.5           # ScaledField -- accepts float
msg['odometer'] = 54231.7

# 3. .set() -- multiple fields at once
msg.set(fuel_level=60, speed=8000, gear=3)

# -- FlagsField set styles -------------------------------------------
msg.status.engine_on  = True     # attribute on the FlagsField
msg.status.handbrake  = False
msg['status']['doors_locked'] = True   # item access into the FlagsField
msg['status']['lights_on']    = True

# ---------------------------------------------------------------------------
# Pretty print before encode -- shows write-side state
# ---------------------------------------------------------------------------

print("=" * 60)
print("BEFORE ENCODE -- write-side state")
print("=" * 60)
print(msg)                       # box-drawn table of all fields

# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------

bits = msg.encode()              # bit string -- ComputedFields calculated here
data = msg.encode_bytes()        # bytes, padded to byte boundary

print("\nBit string :", bits)
print("Bytes       :", data)
print("Write vals  :", msg.write_values)  # capture AFTER encode for computed fields

# ---------------------------------------------------------------------------
# Decode round-trip
# ---------------------------------------------------------------------------

msg.decode(bits)                 # in-place decode from bit string
msg.decode_bytes(data)           # in-place decode from bytes

print("\nRead vals   :", msg.read_values)

# ---------------------------------------------------------------------------
# Reading values -- all styles
# ---------------------------------------------------------------------------

print("\n--- Individual field reads ---")
print("fuel_level.read          :", msg.fuel_level.read)
print("msg['fuel_level'].read   :", msg['fuel_level'].read)
print("speed.read               :", msg.speed.read)
print("engine_temp.read         :", msg.engine_temp.read)
print("odometer.read            :", msg.odometer.read)
print("plate.read               :", msg.plate.read)
print("label.read               :", msg.label.read)
print("throttle.read            :", msg.throttle.read)         # logical float
print("throttle.read_raw        :", msg.throttle.read_raw)     # raw wire integer

print("\n--- FlagsField reads ---")
print("flag_reads               :", msg.status.flag_reads)
print("status.read (packed)     :", msg.status.read)

print("\n--- ComputedField reads ---")
print("seqno.read               :", msg.seqno.read)
print("len.read              :", msg.len.read)
print("checksum.read            :", msg.checksum.read)

# ---------------------------------------------------------------------------
# Pretty print after decode -- both write and read columns populated
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("AFTER DECODE -- both write and read columns")
print("=" * 60)
print(msg)