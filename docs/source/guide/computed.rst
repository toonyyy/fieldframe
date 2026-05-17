Computed Field
==============

:class:`~fieldframe.fields.compute.ComputedField` is a field whose value
is **calculated at encode time** from the other fields in the same message.
It is typically used for checksums, frame lengths, sequence numbers, or any
value that is derived from the payload rather than set directly.

.. code-block:: python

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

The compute function
--------------------

The ``compute`` callable receives the **full sibling field list** as its
only argument. It must return an integer that fits within the field's type.
The list contains every :class:`~fieldframe.frame.component.FrameComponent`
in the message, so you can inspect any field to derive the value you need:

.. code-block:: python

   def frame_length(fields):
       """Return the total number of bytes in the message."""
       return sum(f.length() for f in fields) // 8

   class Frame(Message):
       length  = ComputedField(type=uint_type(8), compute=frame_length)
       payload = Field(type=uint_type(16), default=0)

Encode behaviour
----------------

When :meth:`~fieldframe.core.Message.encode` is called, fieldframe invokes
``compute(fields)`` automatically and encodes the result. The computed
value is also stored in the field's ``write`` attribute so that subsequent
fields or a second encode call can reference it:

.. code-block:: python

   msg = Packet()
   msg.payload.write = 0xAB
   bits = msg.encode()

   print(msg.checksum.write)   # 171 — set automatically at encode time

Decode behaviour
----------------

On **decode**, the compute function is **not** called. The on-wire value
is read directly into :attr:`~fieldframe.fields.compute.ComputedField.read`
so you can verify checksums or lengths after receiving a frame:

.. code-block:: python

   recv = Packet.from_bits(bits)
   print(recv.checksum.read)   # 171 — the value that was on the wire

   # Verify manually
   expected = xor_checksum(recv.fields)
   assert recv.checksum.read == expected

Pretty printing
---------------

.. code-block:: python

   print(msg.checksum)

.. code-block:: text

   ┌─ ComputedField ────────────────────────────┐
   │  name      checksum                        │
   │  type      uint8                           │
   │  fn        xor_checksum                    │
   │  default   0                               │
   │  write     171                             │
   │  read      —                               │
   └────────────────────────────────────────────┘