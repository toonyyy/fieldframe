# fieldframe

[![PyPI version](https://img.shields.io/pypi/v/fieldframe.svg)](https://pypi.org/project/fieldframe/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fieldframe.svg)](https://pypi.org/project/fieldframe/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**fieldframe** is a Python library for defining, encoding, and decoding structured binary messages — built for embedded systems, hardware protocols, and any application where precise bit-level control matters.

Define your message structure once as a Python class. fieldframe handles encoding, decoding, validation, and byte-order concerns automatically.

```python
from fieldframe import Message, Field, uint_type, int_type

class TelemetryMessage(Message):
    speed    = Field(type=uint_type(8),  default=0)
    altitude = Field(type=uint_type(16), default=0)
    heading  = Field(type=int_type(16),  default=0)

msg = TelemetryMessage()

# or

msg = Message(
    Field(name="speed", type=uint_type(8),  default=0)
    Field(name="altitude", type=uint_type(16), default=0)
    Field(name="heading", type=int_type(16),  default=0)
)

msg.speed.write    = 120
msg.altitude.write = 1500
msg.heading.write  = -45

bits  = msg.encode()
# '011110000000010111011101001101'

again = TelemetryMessage.from_bits(bits)
print(again.read_values)
# {'speed': 120, 'altitude': 1500, 'heading': -45}

```

---

## Features

- **Declarative message definitions** — define messages as Python classes with typed field descriptors, or build them dynamically at runtime
- **All common field types** — integers (signed/unsigned, 1–64 bits), IEEE 754 floats (16/32/64-bit), fixed-width strings (ASCII, UTF-8, Latin-1)
- **FlagsField** — pack multiple named boolean flags into a single integer field
- **ScaledField** — store a float as a compact unsigned integer; bit width calculated automatically from range and resolution
- **ComputedField** — derive field values (checksums, lengths, sequence numbers) from sibling fields at encode time
- **Big and little endian** — configurable per message; multi-byte fields byte-swapped automatically
- **Bit reversal** — flip the entire assembled bitstream for LSB-first transports
- **Nested messages** — compose complex frames from reusable sub-messages
- **Protocol routing** — define a `Protocol` with a shared header and key field; incoming frames are dispatched to the correct message type automatically
- **Byte-boundary encoding** — `encode_bytes()` / `decode_bytes()` handle padding to byte boundaries
- **Validation at assignment** — bad values are caught when you set them, not silently corrupted on the wire
- **Pretty printing** — `Message`, `Field`, `FlagsField`, `ScaledField`, and `ComputedField` all support rich box-drawn terminal display via `print()`

---

## Installation

fieldframe is available on [PyPI](https://pypi.org/project/fieldframe/):

```bash
pip install fieldframe
```

Requires Python 3.10 or later.

---

## Quick Start

### Defining a message

There are two ways to define a message: declarative subclassing (recommended for reusable message types) and direct instantiation (useful for one-off or dynamically constructed messages).

**Declarative** — define fields as class variables:

```python
from fieldframe import Message, Field, uint_type, single_type

class SensorFrame(Message):
    sensor_id   = Field(type=uint_type(8),  default=0)
    temperature = Field(type=single_type(), default=0.0)
    status      = Field(type=uint_type(8),  default=0)
```

**Direct instantiation** — pass a field list at construction time:

```python
from fieldframe import Message, Field, uint_type, single_type

msg = Message("SensorFrame", [
    Field(name="sensor_id",   type=uint_type(8),  default=0),
    Field(name="temperature", type=single_type(), default=0.0),
    Field(name="status",      type=uint_type(8),  default=0),
])
```

Both styles encode and decode identically. The declarative style gives you a reusable class and supports `from_bits()` / `from_bytes()`; direct instantiation is better for building messages at runtime or from configuration.

### Encoding

```python
msg = SensorFrame()
msg.sensor_id.write   = 42
msg.temperature.write = 23.5
msg.status.write      = 1

bits = msg.encode()        # bit string
data = msg.encode_bytes()  # bytes, padded to the nearest byte boundary
```

### Decoding

```python
received = SensorFrame()
received.decode(bits)
print(received.read_values)
# {'sensor_id': 42, 'temperature': 23.5, 'status': 1}

# Or decode directly into a new instance
received = SensorFrame.from_bits(bits)
received = SensorFrame.from_bytes(data)
```

---

## Field Types

All type factories are importable directly from `fieldframe`.

### Integer fields

```python
from fieldframe import Field, uint_type, int_type

speed   = Field(type=uint_type(8),  default=0)   # unsigned  0 to 255
heading = Field(type=int_type(16),  default=0)   # signed   -32768 to 32767
flag    = Field(type=uint_type(1),  default=0)   # single bit
```

Any width from 1 to 64 bits is supported.

### Float fields

```python
from fieldframe import Field, single_type, double_type, FloatType

temp = Field(type=single_type(),  default=0.0)  # 32-bit IEEE 754
lat  = Field(type=double_type(),  default=0.0)  # 64-bit IEEE 754
half = Field(type=FloatType(16),  default=0.0)  # 16-bit half precision
```

### String fields

```python
from fieldframe import Field, ascii_type, utf8_type

label    = Field(type=ascii_type(8),  default="")  # 8-byte ASCII, null-padded
callsign = Field(type=utf8_type(32),  default="")  # 32-byte UTF-8
```

Note that string field lengths are in **bytes**, not characters — multibyte UTF-8 characters consume more than one byte each.

---

## Flags Field

Pack multiple named boolean flags into a single integer field — a common pattern in embedded and hardware protocols:

```python
from fieldframe import Message, FlagsField, uint_type

class StatusMessage(Message):
    flags = FlagsField(
        type=uint_type(8),
        flags=["armed", "locked", "error", "ready"],
    )

msg = StatusMessage()
msg.flags.armed = True
msg.flags.ready = True

bits = msg.encode()   # all four flags packed into one byte

recv = StatusMessage.from_bits(bits)
print(recv.flags.flag_reads)
# {'armed': True, 'locked': False, 'error': False, 'ready': True}
```

By default the first flag maps to the MSB (matching hardware spec conventions). Pass `lsb_first=True` to reverse this for CAN or certain SPI configurations.

---

## Scaled Field

Store a floating-point value as a compact unsigned integer on the wire. The bit width is calculated automatically from the range and resolution — no manual sizing needed:

```python
from fieldframe import Message, ScaledField

class SensorFrame(Message):
    # -40 °C to +85 °C in 0.1 °C steps → 11 bits on the wire automatically
    temperature = ScaledField(
        name="temperature",
        min_val=-40.0, max_val=85.0, resolution=0.1,
    )

msg = SensorFrame()
msg.temperature.write = 25.0

bits = msg.encode()
recv = SensorFrame.from_bits(bits)
print(recv.temperature.read)   # 25.0
```

---

## Computed Field

Derive a field's value from sibling fields at encode time — useful for checksums, lengths, and sequence numbers:

```python
from fieldframe import Message, Field, ComputedField, uint_type

def xor_checksum(fields):
    acc = 0
    for f in fields:
        if hasattr(f, "write") and f.name != "checksum":
            acc ^= f.write
    return acc & 0xFF

class Packet(Message):
    payload  = Field(type=uint_type(8), default=0)
    checksum = ComputedField(type=uint_type(8), compute=xor_checksum)

msg = Packet()
msg.payload.write = 0xAB
bits = msg.encode()   # checksum computed automatically from payload
```

On decode the on-wire value is read directly into `checksum.read` so you can verify it against your own calculation.

---

## Byte Order and Bit Reversal

```python
from fieldframe import Message, Field, uint_type

# Little-endian — multi-byte fields are byte-swapped on the wire
class CanFrame(Message, endian="little"):
    value = Field(type=uint_type(16), default=0)

# Bit-reversed — flips the entire bitstream for LSB-first transports
class SpiFrame(Message, reversed=True):
    value = Field(type=uint_type(8), default=0)
```

---

## Nested Messages

Any `Message` instance can be embedded inside another message as a sub-frame. Each sub-message manages its own `endian` and `reversed` settings independently:

```python
from fieldframe import Message, Field, uint_type

class Header(Message):
    version = Field(type=uint_type(4),  default=1)
    msg_id  = Field(type=uint_type(12), default=0)

class TelemetryPacket(Message):
    header   = Header()
    altitude = Field(type=uint_type(16), default=0)

msg = TelemetryPacket()
msg.header.version.write = 2
msg.altitude.write       = 3000
```

---

## Protocol Routing

For protocols with multiple message types sharing a common header, use `Protocol` to handle dispatch automatically. The header is decoded first, the key field is read, and the matching message type is selected:

```python
from fieldframe import Message, Field, uint_type, Protocol

class MyProtocol(Protocol, key="msg_id", name="MyProtocol"):

    class Header(Message):
        msg_id  = Field(type=uint_type(8), default=0)
        version = Field(type=uint_type(8), default=1)

    class TelemetryMessage(Message):
        _msg_id  = 1
        altitude = Field(type=uint_type(16), default=0)

    class CommandMessage(Message):
        _msg_id  = 2
        command  = Field(type=uint_type(8),  default=0)

proto  = MyProtocol()
result = proto.decode(incoming_bits)
# Dispatches to TelemetryMessage or CommandMessage automatically
# based on the msg_id value in the header
```

or 

```python
header = Message(
    "Header", [
        Field(name="msg_id", type=uint_type(8), default=0),
        Field(name="version", type=uint_type(8), default=1)
    ]
)

tele_msg = Message(
    Field(name ="altitude", type=uint_type(16), default=0)
)

cmd_msg(
    Field(name="command", type=uint_type(8),  default=0)
)

proto  = Protcol(
    name = "MyProtocol",
    messages = {
        "1": tele_msg,
        "2": cmd_msg
    },
    header = header,
    key = "msgId"
)
result = proto.decode(incoming_bits)
# Dispatches to TelemetryMessage or CommandMessage automatically
# based on the msg_id value in the header
```


---

## Setting and Reading Values

Every field type follows the same `write` / `read` pattern:

| Action | Syntax |
|---|---|
| Set a field value | `msg.speed.write = 120` |
| Set via message helper | `msg.set(speed=120, heading=0)` |
| Set via item access | `msg['speed'] = 120` |
| Set a flag | `msg.flags.armed = True` |
| Set a flag via item | `msg.flags['armed'] = True` |
| Read last decoded value | `msg.speed.read` |
| Read via item access | `msg['speed'].read` |
| Read all write values | `msg.write_values` |
| Read all decoded values | `msg.read_values` |

Values are validated at assignment time — out-of-range values raise `ValueError` immediately rather than silently corrupting wire data.

---

## Pretty Printing

All field types and `Message` support rich box-drawn terminal display via `print()` or `str()`.

**`Message`** — a table showing every field's name, type, write value, and last decoded read value. Nested sub-messages appear as a summary row and are rendered in full below:

```
┌─ Message: TelemetryPacket  (big-endian, 48 bits) ────────┐
│ name     │ type    │ write  │ read │
├──────────┼─────────┼────────┼──────┤
│ header   │ Message │ 16 b   │      │
│ altitude │ uint16  │ 1500   │ —    │
│ speed    │ uint8   │ 120    │ —    │
└──────────┴─────────┴────────┴──────┘

  ↳ header  (big-endian, 16 bits)
  ┌─────────┬────────┬───────┬──────┐
  │ version │ uint4  │ 1     │ —    │
  │ msg_id  │ uint12 │ 0     │ —    │
  └─────────┴────────┴───────┴──────┘
```

**`Field`** — name, type, default, write value, and read value:

```
┌─ Field ────────────────────────────┐
│  name      speed                   │
│  type      uint8                   │
│  default   0                       │
│  write     120                     │
│  read      —                       │
└────────────────────────────────────┘
```

**`FlagsField`** — each flag with a ✓/✗ indicator plus the packed write and read integers:

```
┌─ FlagsField ──────────────────────────────────────────────┐
│  name      status                                          │
│  type      uint8  (8-bit, lsb_first=False)                 │
│  flags     [✓] armed   [✗] locked   [✗] error   [✓] ready │
│  write     129   read=—                                    │
└────────────────────────────────────────────────────────────┘
```

**`ScaledField`** — range, resolution, step count, wire width, and both logical and raw wire values:

```
┌─ ScaledField ──────────────────────────────┐
│  name        temperature                   │
│  range       [-40.0, 85.0]                 │
│  resolution  0.1                           │
│  steps       1250  (11-bit wire)           │
│  write       25.0  (wire=650)              │
│  read        —     (wire=—)                │
└────────────────────────────────────────────┘
```

**`ComputedField`** — compute function name, default, last computed write value, and last decoded read value:

```
┌─ ComputedField ────────────────────────────┐
│  name      checksum                        │
│  type      uint8                           │
│  fn        xor_checksum                    │
│  default   0                               │
│  write     171                             │
│  read      —                               │
└────────────────────────────────────────────┘
```

**`Protocol.display()`** — prints the protocol name followed by the full message table for every registered message type:

```python
proto.display()
# Protocol: MyProtocol
# ┌─ Message: TelemetryMessage ...
# ┌─ Message: CommandMessage ...
```

---

## Use Cases

fieldframe is well suited for:

- **CAN bus and automotive protocols** — define frames with scaled physical values, flags bytes, and little-endian byte order
- **Serial and UART protocols** — encode and decode fixed-width binary frames over RS-232, RS-485, or similar transports
- **SPI and I2C device registers** — map register layouts to named fields with bit-level precision
- **UAV and robotics telemetry** — structured telemetry frames between flight controllers, ground stations, and sensors
- **Custom binary wire formats** — any application where you need to pack structured data into a compact binary representation
- **Protocol testing and simulation** — build message structures in Python to generate test vectors or validate hardware implementations

---

## Requirements

- Python >= 3.10
- [bitarray](https://github.com/ilanschnell/bitarray) >= 3.8.1

---

## License

MIT