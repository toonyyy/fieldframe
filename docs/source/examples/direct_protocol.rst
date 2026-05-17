Direct Protocol
===============

Demonstrates defining a full multi-message protocol by passing message
instances **directly to the** :class:`~fieldframe.protocols.Protocol`
**constructor** — no subclassing required. Every message and the header are
constructed as ``Message("name", [...])`` instances and passed in.

`View on GitHub <https://github.com/frasertoon/fieldframe/blob/main/examples/direct_protocol.py>`_

----

What this example covers
-------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 0

   * - Protocol direct instantiation
     - ``name=``, ``header=``, ``key=``, ``messages=`` constructor arguments
   * - Header as a plain Message instance
     - Constructed with ``Message("Header", [...])`` and passed to ``header=``
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

Declarative vs direct protocols — the only difference
------------------------------------------------------

Both protocol examples define an identical ``CarProtocol``. The only
difference is construction syntax:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Declarative
     - Direct
   * - ``class CarProtocol(Protocol, key="msg_id"):``
     - ``protocol = Protocol(name=..., header=..., key=..., messages=...)``
   * - ``class Header(Message):``
     - ``header = Message("Header", [...])``
   * - ``class Heartbeat(Message):`` with ``_msg_id = "1"``
     - ``heartbeat = Message("Heartbeat", [...])`` passed under key ``"1"``
   * - Best for fixed protocols known at import time
     - Best for protocols built at runtime or from configuration

----

Building the header
-------------------

.. code-block:: python

    from fieldframe import (
        Message, Field, FlagsField, ScaledField, ComputedField,
        uint_type, int_type, single_type, ascii_type,
    )
    from fieldframe.protocols import Protocol

    header = Message("Header", [
        Field(name="msg_id",  type=uint_type(8), default=0),
        Field(name="ecu_id",  type=uint_type(8), default=0),
        Field(name="version", type=uint_type(4), default=1),
    ])

Building the messages
---------------------

Each message is a plain :class:`~fieldframe.core.Message` instance with
``crc`` as its last field:

.. code-block:: python

    heartbeat = Message("Heartbeat", [
        Field(name="unit_id", type=uint_type(8),  default=1),
        Field(name="uptime",  type=uint_type(32), default=0),
        Field(name="vin",     type=ascii_type(6), default=""),
        FlagsField(name="state", type=uint_type(8),
                   flags=["online", "healthy", "busy", "degraded"]),
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ])

    vehicle_status = Message("VehicleStatus", [
        FlagsField(name="flags", type=uint_type(8),
                   flags=["engine_on", "handbrake", "fault", "door_open"]),
        Field(name="speed",    type=uint_type(8),  default=0),
        Field(name="rpm",      type=uint_type(16), default=0),
        Field(name="fuel_pct", type=uint_type(8),  default=100),
        Field(name="gear",     type=int_type(8),   default=0),
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ])

    wheel_command = Message("WheelCommand", [
        Field(name="wheel_id",  type=uint_type(4), default=0),
        Field(name="direction", type=int_type(8),  default=0),
        ScaledField(name="torque", min_val=0.0, max_val=100.0, resolution=0.5),
        ComputedField(name="crc", type=uint_type(8), compute=frame_crc, default=0),
    ], endian="little")

    diagnostic_log = Message("DiagnosticLog", [
        Field(name="timestamp",    type=uint_type(32), default=0),
        Field(name="engine_temp",  type=int_type(16),  default=0),
        Field(name="oil_pressure", type=uint_type(16), default=0),
        Field(name="battery_mv",   type=uint_type(16), default=0),
        Field(name="intake_temp",  type=int_type(8),   default=0),
        Field(name="throttle_pos", type=uint_type(8),  default=0),
        Field(name="brake_press",  type=uint_type(8),  default=0),
        ComputedField(name="length", type=uint_type(8), compute=payload_length, default=0),
        ComputedField(name="crc",    type=uint_type(8), compute=frame_crc,      default=0),
    ])

Instantiating the protocol
---------------------------

.. code-block:: python

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

Encoding — always via the protocol's registered instance
---------------------------------------------------------

.. code-block:: python

    # CORRECT -- header already injected, crc sees the full frame
    hb   = protocol.messages["1"]
    bits = hb.encode()

    # WRONG -- bare instance has no header, crc is incomplete
    bits = heartbeat.encode()

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

.. literalinclude:: ../../../examples/direct_protocol.py
   :language: python
   :caption: examples/direct_protocol.py
   :linenos: