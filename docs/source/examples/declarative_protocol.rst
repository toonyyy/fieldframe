Declarative Protocol
====================

Demonstrates defining a full multi-message protocol by **subclassing**
:class:`~fieldframe.protocols.Protocol`. Nested ``Message`` classes named
``Header`` are picked up automatically. Any other nested ``Message`` subclass
with a ``_msg_id`` attribute is registered as a typed message under that key.

`View on GitHub <https://github.com/frasertoon/fieldframe/blob/main/examples/declarative_protocol.py>`_

----

What this example covers
-------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 0

   * - Protocol subclassing
     - ``key=`` and ``name=`` class keywords
   * - Header auto-injection
     - Deep-copied and prepended to every registered message automatically
   * - Five message types
     - All field families including little-endian and sub-byte fields
   * - Whole-frame CRC
     - ``ComputedField`` as the last field in each message, covering the
       full frame including injected header fields
   * - ``get_message()``
     - Look up a registered message by its name attribute
   * - Encode pattern
     - Always via ``protocol.messages[key]``, never a bare instance
   * - ``decode()``
     - Protocol routes by key field automatically
   * - ``display()``
     - Pretty print all registered messages

----

Protocol structure
------------------

The ``CarProtocol`` defines five message types. Every frame on the wire
follows this layout:

.. code-block:: text

    [ Header: msg_id(8)  ecu_id(8)  version(4) ]
    [ Payload: varies by message type           ]
    [ crc(8): XOR of all preceding int fields   ]

The header is prepended automatically. The ``crc`` field is the last
:class:`~fieldframe.fields.compute.ComputedField` inside each message —
because it runs after all other fields it sees the complete flattened
field list including the injected header fields, giving a true whole-frame
integrity check.

----

Protocol definition
-------------------

.. code-block:: python

    from fieldframe import (
        Message, Field, FlagsField, ScaledField, ComputedField,
        uint_type, int_type, single_type, ascii_type,
    )
    from fieldframe.protocols import Protocol

    class CarProtocol(Protocol, key="msg_id", name="CarProtocol"):

        class Header(Message):
            msg_id  = Field(type=uint_type(8), default=0)
            ecu_id  = Field(type=uint_type(8), default=0)
            version = Field(type=uint_type(4), default=1)

        class Heartbeat(Message):
            _msg_id   = "1"
            unit_id   = Field(type=uint_type(8),  default=1)
            uptime    = Field(type=uint_type(32), default=0)
            vin       = Field(type=ascii_type(6), default="")
            state     = FlagsField(type=uint_type(8), flags=["online", "healthy", "busy", "degraded"])
            crc       = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

        class VehicleStatus(Message):
            _msg_id   = "2"
            flags     = FlagsField(type=uint_type(8), flags=["engine_on", "handbrake", "fault", "door_open"])
            speed     = Field(type=uint_type(8),  default=0)
            rpm       = Field(type=uint_type(16), default=0)
            fuel_pct  = Field(type=uint_type(8),  default=100)
            gear      = Field(type=int_type(8),   default=0)
            crc       = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

        class GpsPosition(Message):
            _msg_id    = "3"
            latitude   = Field(type=single_type(), default=0.0)
            longitude  = Field(type=single_type(), default=0.0)
            altitude_m = Field(type=uint_type(16), default=0)
            satellites = Field(type=uint_type(8),  default=0)
            hdop       = Field(type=uint_type(8),  default=0)
            crc        = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

        class WheelCommand(Message, endian="little"):
            _msg_id   = "4"
            wheel_id  = Field(type=uint_type(4), default=0)
            direction = Field(type=int_type(8),  default=0)
            torque    = ScaledField(name="torque", min_val=0.0, max_val=100.0, resolution=0.5)
            crc       = ComputedField(type=uint_type(8), compute=frame_crc, default=0)

        class DiagnosticLog(Message):
            _msg_id      = "5"
            timestamp    = Field(type=uint_type(32), default=0)
            engine_temp  = Field(type=int_type(16),  default=0)
            oil_pressure = Field(type=uint_type(16), default=0)
            battery_mv   = Field(type=uint_type(16), default=0)
            intake_temp  = Field(type=int_type(8),   default=0)
            throttle_pos = Field(type=uint_type(8),  default=0)
            brake_press  = Field(type=uint_type(8),  default=0)
            length       = ComputedField(type=uint_type(8), compute=payload_length, default=0)
            crc          = ComputedField(type=uint_type(8), compute=frame_crc,      default=0)

CRC design
----------

The ``frame_crc`` function is placed last in every message as a
:class:`~fieldframe.fields.compute.ComputedField`. It skips itself and XORs
every other integer write value in the frame — including the injected header
fields — for a true whole-frame check:

.. code-block:: python

    def frame_crc(fields):
        acc = 0
        for f in fields:
            if f.name == "crc":
                continue
            val = getattr(f, "write", None)
            if isinstance(val, int):
                acc ^= val & 0xFF
        return acc & 0xFF

Encoding — always via the protocol's registered instance
---------------------------------------------------------

.. code-block:: python

    protocol = CarProtocol()

    # CORRECT -- header already injected, crc sees the full frame
    hb   = protocol.messages["1"]
    bits = hb.encode()

    # WRONG -- bare instance has no header, crc is incomplete
    bits = Heartbeat().encode()

Encode/decode round-trips
--------------------------

.. code-block:: python

    # Heartbeat
    hb = protocol.messages["1"]
    hb.unit_id.write  = 3
    hb.uptime.write   = 7200
    hb['vin']         = "1HGCM8"
    hb.state.online   = True
    hb.state.healthy  = True

    bits   = hb.encode()
    result = protocol.decode(bits)
    print("Sent   :", hb.write_values)
    print("Decoded:", result)

    # GpsPosition
    gps = protocol.messages["3"]
    gps.latitude.write  = -33.8688
    gps.longitude.write = 151.2093
    gps.set(altitude_m=58, satellites=11, hdop=8)

    bits   = gps.encode()
    result = protocol.decode(bits)

    # WheelCommand (little-endian)
    wc = protocol.messages["4"]
    wc.wheel_id.write  = 2
    wc.direction.write = -1
    wc['torque']       = 45.0

    bits   = wc.encode()
    result = protocol.decode(bits)

    # DiagnosticLog -- look up by name
    dl = protocol.get_message("DiagnosticLog")
    dl['timestamp']    = 1_700_000_000
    dl['engine_temp']  = 9230
    dl.set(oil_pressure=280, battery_mv=12650, throttle_pos=42)

    bits   = dl.encode()
    result = protocol.decode(bits)

    # Pretty print all registered messages
    protocol.display()

Full source
-----------

.. literalinclude:: ../../../examples/declarative_protocol.py
   :language: python
   :caption: examples/declarative_protocol.py
   :linenos: