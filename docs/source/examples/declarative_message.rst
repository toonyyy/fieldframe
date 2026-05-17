Declarative Message
===================

Demonstrates defining a single message by **subclassing**
:class:`~fieldframe.core.Message`. Fields are declared as class variables
and fieldframe assigns their names automatically from the attribute name —
no ``name=`` argument needed.

This is the recommended style for fixed, reusable message types.

`View on GitHub <https://github.com/frasertoon/fieldframe/blob/main/examples/declarative_message.py>`_

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

Message definition
------------------

The message is defined by subclassing :class:`~fieldframe.core.Message`.
Every field declared as a class variable is registered automatically:

.. code-block:: python

    from fieldframe import (
        Message, Field, FlagsField, ScaledField, ComputedField,
        uint_type, int_type, single_type, double_type, ascii_type, utf8_type,
    )

    class VehicleData(Message):
        unit_id     = Field(type=uint_type(8),   default=1)
        gear        = Field(type=int_type(8),    default=0)
        fuel_level  = Field(type=uint_type(8),   default=100)
        speed       = Field(type=int_type(16),   default=0)
        engine_temp = Field(type=single_type(),  default=0.0)
        odometer    = Field(type=double_type(),  default=0.0)
        plate       = Field(type=ascii_type(6),  default="")
        label       = Field(type=utf8_type(16),  default="")
        throttle    = ScaledField(name="throttle", min_val=0.0, max_val=100.0, resolution=0.5)
        status      = FlagsField(type=uint_type(8), flags=["engine_on", "handbrake", "doors_locked", "lights_on"], lsb_first=True)
        seqno       = ComputedField(type=uint_type(8), compute=increase,     default=0)
        length      = ComputedField(type=uint_type(8), compute=msg_length,   default=0)
        checksum    = ComputedField(type=uint_type(8), compute=xor_checksum, default=0)

ComputedField functions
-----------------------

Three compute functions are defined before the class. They receive the
full sibling field list at encode time:

.. code-block:: python

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

Setting values
--------------

All three set styles work for any field type:

.. code-block:: python

    msg = VehicleData()

    # 1. Direct .write attribute
    msg.gear.write        = -1
    msg.fuel_level.write  = 85
    msg.engine_temp.write = 92.3
    msg.odometer.write    = 54231.7

    # 2. Item assignment
    msg['unit_id']  = 7
    msg['speed']    = -250
    msg['plate']    = "ABC123"
    msg['label']    = "delivery-van"
    msg['throttle'] = 22.5

    # 3. .set() — multiple fields at once
    msg.set(fuel_level=60, speed=8000, gear=3)

    # FlagsField — attribute and item access
    msg.status.engine_on      = True
    msg['status']['doors_locked'] = True

Encoding
--------

Call ``encode()`` after setting all values. Capture ``write_values`` after
encode so :class:`~fieldframe.fields.compute.ComputedField` values (seqno,
length, checksum) reflect what was actually written to the wire:

.. code-block:: python

    bits = msg.encode()        # bit string
    data = msg.encode_bytes()  # bytes, padded to byte boundary

    print(msg.write_values)    # capture AFTER encode

Reading values
--------------

All read styles return the decoded value after a decode call:

.. code-block:: python

    msg.decode(bits)
    msg.decode_bytes(data)

    # .read attribute
    print(msg.fuel_level.read)

    # item access
    print(msg['fuel_level'].read)

    # all decoded values at once
    print(msg.read_values)

    # FlagsField
    print(msg.status.flag_reads)   # {name: bool} dict
    print(msg.status.read)         # packed integer

    # ScaledField
    print(msg.throttle.read)       # logical float
    print(msg.throttle.read_raw)   # raw wire integer

    # ComputedField
    print(msg.seqno.read)
    print(msg.length.read)
    print(msg.checksum.read)

Full source
-----------

.. literalinclude:: ../../../examples/declarative_message.py
   :language: python
   :caption: examples/declarative_message.py
   :linenos: