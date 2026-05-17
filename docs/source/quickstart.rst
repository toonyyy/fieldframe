Quick Start
===========

This page walks through the core fieldframe workflow — define, encode,
decode — in a few minutes.

Defining a message
------------------

The recommended way is to subclass :class:`~fieldframe.core.Message` and
declare fields as class variables:

.. code-block:: python

   from fieldframe import Message, Field, uint_type, int_type

   class TelemetryMessage(Message):
       speed    = Field(type=uint_type(8),  default=0)
       altitude = Field(type=uint_type(16), default=0)
       heading  = Field(type=int_type(16),  default=0)

You can also build a message directly at runtime without subclassing:

.. code-block:: python

   from fieldframe import Message, Field, uint_type, int_type

   msg = Message("TelemetryMessage", [
       Field(name="speed",    type=uint_type(8),  default=0),
       Field(name="altitude", type=uint_type(16), default=0),
       Field(name="heading",  type=int_type(16),  default=0),
   ])

See :doc:`guide/messages` for a full comparison of both styles.

Setting values
--------------

Assign values to the ``write`` attribute of each field before encoding.
Values are validated immediately — out-of-range assignments raise
:exc:`ValueError` at the point of assignment:

.. code-block:: python

   msg = TelemetryMessage()
   msg.speed.write    = 120
   msg.altitude.write = 1500
   msg.heading.write  = -45

   # Alternative shorthand via the message
   msg.set(speed=120, altitude=1500, heading=-45)

Encoding
--------

Call :meth:`~fieldframe.core.Message.encode` to produce a bit string, or
:meth:`~fieldframe.core.Message.encode_bytes` to get a byte-padded
:class:`bytes` object:

.. code-block:: python

   bits = msg.encode()        # '011110000000010111011101001101'
   data = msg.encode_bytes()  # b'\x78\x05\xd3'

Decoding
--------

Pass a bit string to :meth:`~fieldframe.core.Message.decode`, or use the
class methods :meth:`~fieldframe.core.Message.from_bits` and
:meth:`~fieldframe.core.Message.from_bytes` to decode directly into a fresh
instance:

.. code-block:: python

   received = TelemetryMessage()
   received.decode(bits)

   print(received.speed.read)     # 120
   print(received.read_values)    # {'speed': 120, 'altitude': 1500, 'heading': -45}

   # Decode into a new instance directly
   received = TelemetryMessage.from_bits(bits)
   received = TelemetryMessage.from_bytes(data)

Inspecting a message
--------------------

Calling ``print()`` on any message or field renders a box-drawn table in
the terminal:

.. code-block:: python

   print(received)

.. code-block:: text

   ┌─ Message: TelemetryMessage  (big-endian, 40 bits) ───────────┐
   │ name     │ type   │ write │ read │
   ├──────────┼────────┼───────┼──────┤
   │ speed    │ uint8  │ 120   │ 120  │
   │ altitude │ uint16 │ 1500  │ 1500 │
   │ heading  │ int16  │ -45   │ -45  │
   └──────────┴────────┴───────┴──────┘

Next steps
----------

- :doc:`guide/messages` — declarative vs direct instantiation in detail
- :doc:`guide/field_types` — integers, floats, and strings
- :doc:`guide/values` — all the ways to get and set field values
- :doc:`guide/flags` — named boolean flags packed into a single field
- :doc:`guide/scaled` — float values stored as compact integers
- :doc:`guide/computed` — checksums and derived fields
- :doc:`guide/protocols` — multi-message protocol routing
- :doc:`examples/index` — runnable example scripts covering all field types and both construction styles