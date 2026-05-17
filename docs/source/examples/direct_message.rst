Direct Message
==============

Demonstrates defining a single message by passing a **field list directly**
to the :class:`~fieldframe.core.Message` constructor — no subclassing
required. Every field must be given an explicit ``name=`` argument because
there is no class body for fieldframe to read attribute names from.

This style is better suited for messages built at runtime or from
configuration data where the structure is not known at import time.

`View on GitHub <https://github.com/frasertoon/fieldframe/blob/main/examples/direct_message.py>`_

----

What this example covers
-------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 0

   * - :class:`~fieldframe.fields.field.Field`
     - ``uint_type``, ``int_type``, ``single_type``, ``double_type``,
       ``ascii_type``, ``utf8_type``
   * - :class:`~fieldframe.fields.scaled.ScaledField`
     - Float stored as a compact unsigned integer, bit width auto-calculated
   * - :class:`~fieldframe.fields.flags.FlagsField`
     - Named boolean bits packed into a single integer field
   * - :class:`~fieldframe.fields.compute.ComputedField`
     - Sequence number, frame length, and XOR checksum
   * - Set styles
     - ``.write``, ``[]``, ``.set()``, flag attribute, flag item
   * - Get styles
     - ``.read``, ``[]``, ``.read_values``, ``.write_values``, ``.flag_reads``
   * - Encode / decode
     - Bit string and bytes round-trip

----

Declarative vs direct — the only difference
--------------------------------------------

Both message examples define an identical ``VehicleData`` message. The only
difference is construction syntax:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Declarative
     - Direct
   * - ``class VehicleData(Message):``
     - ``msg = Message("VehicleData", [...])``
   * - Field names inferred from attribute names
     - Field names must be passed as ``name=``
   * - Supports ``from_bits()`` / ``from_bytes()``
     - Encode/decode only via instance methods
   * - Best for fixed, reusable types
     - Best for runtime or config-driven construction

----

Message construction
--------------------

The message is built by passing a list of field instances directly to the
:class:`~fieldframe.core.Message` constructor. Every field requires an
explicit ``name=`` argument:

.. code-block:: python

    from fieldframe import (
        Message, Field, FlagsField, ScaledField, ComputedField,
        uint_type, int_type, single_type, double_type, ascii_type, utf8_type,
    )

    msg = Message("VehicleData", [
        Field(name="unit_id",     type=uint_type(8),   default=1),
        Field(name="gear",        type=int_type(8),    default=0),
        Field(name="fuel_level",  type=uint_type(8),   default=100),
        Field(name="speed",       type=int_type(16),   default=0),
        Field(name="engine_temp", type=single_type(),  default=0.0),
        Field(name="odometer",    type=double_type(),  default=0.0),
        Field(name="plate",       type=ascii_type(6),  default=""),
        Field(name="label",       type=utf8_type(16),  default=""),
        ScaledField(name="throttle", min_val=0.0, max_val=100.0, resolution=0.5),
        FlagsField(name="status", type=uint_type(8),
                   flags=["engine_on", "handbrake", "doors_locked", "lights_on"],
                   lsb_first=True),
        ComputedField(name="seqno",    type=uint_type(8), compute=increase,     default=0),
        ComputedField(name="length",   type=uint_type(8), compute=msg_length,   default=0),
        ComputedField(name="checksum", type=uint_type(8), compute=xor_checksum, default=0),
    ])

Setting values
--------------

The set styles are identical to the declarative example — construction style
has no effect on how you interact with fields:

.. code-block:: python

    # 1. Direct .write attribute
    msg.gear.write        = -1
    msg.fuel_level.write  = 85
    msg.engine_temp.write = 92.3

    # 2. Item assignment
    msg['unit_id']  = 7
    msg['speed']    = -250
    msg['plate']    = "ABC123"
    msg['throttle'] = 22.5

    # 3. .set() — multiple fields at once
    msg.set(fuel_level=60, speed=8000, gear=3)

    # FlagsField — attribute and item access
    msg.status.engine_on          = True
    msg['status']['doors_locked'] = True

Encoding
--------

.. code-block:: python

    bits = msg.encode()        # bit string
    data = msg.encode_bytes()  # bytes, padded to byte boundary

    print(msg.write_values)    # capture AFTER encode for computed fields

Reading values
--------------

.. code-block:: python

    msg.decode(bits)
    msg.decode_bytes(data)

    print(msg.fuel_level.read)      # .read attribute
    print(msg['fuel_level'].read)   # item access

    print(msg.read_values)          # all decoded values

    print(msg.status.flag_reads)    # {name: bool} dict
    print(msg.status.read)          # packed integer

    print(msg.throttle.read)        # logical float
    print(msg.throttle.read_raw)    # raw wire integer

    print(msg.seqno.read)
    print(msg.length.read)
    print(msg.checksum.read)

Full source
-----------

.. literalinclude:: ../../../examples/direct_message.py
   :language: python
   :caption: examples/direct_message.py
   :linenos: