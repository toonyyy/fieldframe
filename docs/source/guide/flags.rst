Flags Field
===========

:class:`~fieldframe.fields.flags.FlagsField` packs multiple named boolean
flags into a single unsigned integer field on the wire. This is a very
common pattern in embedded and hardware protocols — rather than defining
eight separate 1-bit fields for a status byte, you declare one
:class:`~fieldframe.fields.flags.FlagsField`:

.. code-block:: python

   from fieldframe import Message, FlagsField, uint_type

   class StatusMessage(Message):
       flags = FlagsField(
           type=uint_type(8),
           flags=["armed", "locked", "error", "ready"],
       )

Defining flags
--------------

The ``flags`` parameter is a list of names. Each name corresponds to one
bit in the field, working from the MSB by default:

.. list-table::
   :header-rows: 1
   :widths: 20 20 20 20 20

   * - Bit 7
     - Bit 6
     - Bit 5
     - Bit 4
     - Bits 3–0
   * - armed
     - locked
     - error
     - ready
     - (reserved 0)

You do not need to fill all bits — unused lower bits are reserved as zero
automatically.

Setting flags
-------------

Flags can be set via attribute access, item access, or direct assignment
to the ``write`` property:

.. code-block:: python

   msg = StatusMessage()

   # Attribute access — most natural
   msg.flags.armed = True
   msg.flags.ready = True

   # Item access — useful when the flag name is a variable
   msg.flags["armed"] = True

   # Check a flag's current write-side value
   if msg.flags.armed:
       print("Armed!")

Reading decoded flags
---------------------

After decoding, use :attr:`~fieldframe.fields.flags.FlagsField.flag_reads`
to get all decoded flag states as a dictionary, or access individual flags
via attribute access — the same syntax works for both write and read paths:

.. code-block:: python

   recv = StatusMessage.from_bits(bits)

   # Full decoded state as a dict
   print(recv.flags.flag_reads)
   # {'armed': True, 'locked': False, 'error': False, 'ready': True}

   # Packed integer of the decoded state
   print(recv.flags.read)   # e.g. 144

Bit ordering
------------

By default (``lsb_first=False``) the **first flag name maps to the MSB**.
This matches the way hardware protocol specifications are typically written
(*"bit 7 = armed"*).

Pass ``lsb_first=True`` for protocols that address bit 0 first, which is
common in CAN and certain SPI configurations:

.. code-block:: python

   flags = FlagsField(
       type=uint_type(8),
       flags=["armed", "locked", "error", "ready"],
       lsb_first=True,   # armed → bit 0, locked → bit 1, ...
   )

Pretty printing
---------------

.. code-block:: python

   print(msg.flags)

.. code-block:: text

   ┌─ FlagsField ──────────────────────────────────────────────┐
   │  name      status                                          │
   │  type      uint8  (8-bit, lsb_first=False)                 │
   │  flags     [✓] armed   [✗] locked   [✗] error   [✓] ready │
   │  write     129   read=—                                    │
   └────────────────────────────────────────────────────────────┘