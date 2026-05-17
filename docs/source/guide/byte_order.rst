Byte Order and Bit Reversal
===========================

fieldframe gives you two independent controls over how bits are laid out
on the wire: **endianness** (byte order within multi-byte fields) and
**bit reversal** (flipping the entire assembled bitstream).

Endianness
----------

Set ``endian`` as a class keyword argument on a declarative message, or
pass it to the :class:`~fieldframe.core.Message` constructor directly:

.. code-block:: python

   from fieldframe import Message, Field, uint_type

   class BigEndianFrame(Message, endian="big"):      # default
       value = Field(type=uint_type(16), default=0)

   class LittleEndianFrame(Message, endian="little"):
       value = Field(type=uint_type(16), default=0)

The default is ``"big"``.

**How it works:**

For a 16-bit field with value ``0x1234``:

- Big-endian wire order: ``00010010 00110100`` (MSB first)
- Little-endian wire order: ``00110100 00010010`` (LSB byte first)

Only **multi-byte fields** (> 8 bits) are affected. Single-byte and
sub-byte fields are never swapped.

Nested sub-messages manage their own ``endian`` setting independently of
their parent — a little-endian parent can contain a big-endian sub-message.

Bit reversal
------------

Some transports (certain SPI and UART configurations) transmit bits LSB
first, which means the entire assembled bitstream needs to be flipped before
transmission and after reception.

Pass ``reversed=True`` to flip the complete bit string produced by
:meth:`~fieldframe.core.Message.encode`:

.. code-block:: python

   class SpiFrame(Message, reversed=True):
       value = Field(type=uint_type(8), default=0xAB)

   msg = SpiFrame()
   print(msg.encode())   # '11010101'  (0xAB reversed)

Bit reversal is applied **after** all field encoding and endian byte-swapping
— it is purely a transport-layer concern and does not affect the logical
values of any field.

On decode, bit reversal is applied **before** field decoding so the logical
values are always correct.

Combining both
--------------

Endianness and bit reversal can be combined independently:

.. code-block:: python

   class ComboFrame(Message, endian="little", reversed=True):
       value = Field(type=uint_type(16), default=0)