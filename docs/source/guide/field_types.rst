Field Types
===========

fieldframe supports three families of field types — integers, floats, and
strings. All type factories are importable directly from ``fieldframe``.

Every type implements the same internal interface:

- ``bits`` — total wire width in bits
- ``validate(value)`` — raises :exc:`TypeError` or :exc:`ValueError` if invalid
- ``encode_bits(value, endian)`` — returns a ``'0'``/``'1'`` bit string
- ``decode_bits(bit_str, endian)`` — returns the decoded Python value

You never call these methods directly — :class:`~fieldframe.fields.field.Field`
calls them automatically during encode and decode.

Integer types
-------------

:class:`~fieldframe.types.int.IntType` describes a fixed-width binary integer.
Any width from 1 to 64 bits is supported, signed or unsigned:

.. code-block:: python

   from fieldframe import Field, uint_type, int_type

   speed   = Field(type=uint_type(8),  default=0)   # unsigned  0 to 255
   heading = Field(type=int_type(16),  default=0)   # signed   -32768 to 32767
   flag    = Field(type=uint_type(1),  default=0)   # single bit

:func:`~fieldframe.types.int.uint_type` creates an unsigned integer type.
:func:`~fieldframe.types.int.int_type` creates a signed two's-complement integer type.

You can also instantiate :class:`~fieldframe.types.int.IntType` directly:

.. code-block:: python

   from fieldframe import IntType

   my_type = IntType(bits=12, signed=False)   # 12-bit unsigned, 0 to 4095

Range validation happens at assignment time — assigning an out-of-range
value raises :exc:`ValueError` immediately:

.. code-block:: python

   f = Field(name="speed", type=uint_type(8), default=0)
   f.write = 255    # OK
   f.write = 256    # raises ValueError

String representations:

.. code-block:: python

   >>> uint_type(8)
   IntType(uint8  range=[0, 255])
   >>> int_type(16)
   IntType(int16  range=[-32768, 32767])

Float types
-----------

:class:`~fieldframe.types.float.FloatType` describes an IEEE 754
floating-point field. Three widths are supported: 16-bit (half), 32-bit
(single), and 64-bit (double) — matching the formats the Python
:mod:`struct` module supports directly:

.. code-block:: python

   from fieldframe import Field, single_type, double_type, FloatType

   temp  = Field(type=single_type(),  default=0.0)   # 32-bit IEEE 754
   lat   = Field(type=double_type(),  default=0.0)   # 64-bit IEEE 754
   half  = Field(type=FloatType(16),  default=0.0)   # 16-bit half precision

Convenience factories:

.. list-table::
   :header-rows: 1
   :widths: 25 15 60

   * - Factory
     - Bits
     - Range
   * - ``FloatType(16)``
     - 16
     - ±65504.0
   * - ``single_type()``
     - 32
     - ±3.4028 × 10³⁸
   * - ``double_type()``
     - 64
     - ±1.7977 × 10³⁰⁸

By default ``±inf`` and ``NaN`` are rejected by validation. To permit them,
pass ``allow_special=True``:

.. code-block:: python

   from fieldframe import FloatType

   permissive = FloatType(bits=32, allow_special=True)

String types
------------

:class:`~fieldframe.types.string.StringType` describes a fixed-width string
field. The ``length`` parameter is always in **bytes**, not characters —
multibyte UTF-8 characters consume more than one byte each:

.. code-block:: python

   from fieldframe import Field, ascii_type, utf8_type

   label    = Field(type=ascii_type(8),  default="")   # 8-byte ASCII, null-padded
   callsign = Field(type=utf8_type(32),  default="")   # 32-byte UTF-8

Convenience factories:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Factory
     - Description
   * - ``ascii_type(n)``
     - n-byte ASCII field, null-padded
   * - ``utf8_type(n)``
     - n-byte UTF-8 field, null-padded
   * - ``StringType(n, encoding, pad)``
     - Full control over encoding and pad character

Short strings are right-padded to the full field width with the pad
character (default ``\x00``). On decode, trailing pad characters are
stripped automatically.

To use space-padding instead of null-padding (common in legacy protocols):

.. code-block:: python

   from fieldframe import StringType

   padded = StringType(length=8, encoding="ascii", pad=" ")

Endianness and strings
^^^^^^^^^^^^^^^^^^^^^^

Endianness has no effect on string fields — bytes are always written and
read left-to-right regardless of the message ``endian`` setting.