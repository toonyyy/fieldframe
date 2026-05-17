Messages
========

A :class:`~fieldframe.core.Message` is the central object in fieldframe.
It is a container of :class:`~fieldframe.frame.component.FrameComponent`
items — fields, flag fields, scaled fields, computed fields, or other
nested messages — that together form one complete binary frame.

Declarative style
-----------------

The recommended way to define a message is to subclass
:class:`~fieldframe.core.Message` and declare fields as class variables.
fieldframe picks up every :class:`~fieldframe.frame.component.FrameComponent`
declared on the class body, names it automatically from the attribute name,
and stores it as a template that is deep-copied for every instance:

.. code-block:: python

   from fieldframe import Message, Field, uint_type, int_type

   class GuidanceMessage(Message):
       speed   = Field(type=uint_type(8),  default=0)
       heading = Field(type=int_type(16),  default=0)

   msg = GuidanceMessage()

This style is best for fixed, reusable message types.  It also enables the
class-method constructors :meth:`~fieldframe.core.Message.from_bits` and
:meth:`~fieldframe.core.Message.from_bytes`.

Direct instantiation
--------------------

For one-off or dynamically constructed messages, pass a list of fields
directly to the :class:`~fieldframe.core.Message` constructor.  Every field
must be given an explicit ``name`` in this style because there is no class
body for fieldframe to read names from:

.. code-block:: python

   from fieldframe import Message, Field, uint_type, int_type

   msg = Message("GuidanceMessage", [
       Field(name="speed",   type=uint_type(8),  default=0),
       Field(name="heading", type=int_type(16),  default=0),
   ])

Both styles are fully equivalent for encoding and decoding.

Byte order
----------

Pass ``endian="little"`` as a class keyword argument (declarative) or as a
constructor parameter (direct) to byte-swap all multi-byte fields:

.. code-block:: python

   class CanFrame(Message, endian="little"):
       value = Field(type=uint_type(16), default=0)

   # or directly:
   msg = Message("CanFrame", [...], endian="little")

The default is ``"big"``.  See :doc:`byte_order` for full details.

Nested messages
---------------

Any :class:`~fieldframe.core.Message` instance can be used as a field
inside another message.  Each sub-message manages its own ``endian`` and
``reversed`` settings independently of its parent:

.. code-block:: python

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

When printed, sub-messages appear as a summary row in the parent table and
are rendered in full below it.

Dynamic field manipulation
--------------------------

Fields can be added or removed from a message instance at runtime using
:meth:`~fieldframe.core.Message.add_field` and
:meth:`~fieldframe.core.Message.remove_field`:

.. code-block:: python

   from fieldframe import Message, Field, uint_type

   msg = Message("Dynamic", [])
   msg.add_field(Field(name="speed", type=uint_type(8), default=0))
   msg.add_field(Field(name="flags", type=uint_type(8), default=0), position=0)
   msg.remove_field(position=1)

Encoding and decoding
---------------------

.. code-block:: python

   bits = msg.encode()              # → bit string
   data = msg.encode_bytes()        # → bytes, padded to byte boundary

   msg.decode(bits)                 # decode in-place
   values = msg.read_values         # {'speed': ..., 'heading': ...}

   msg2 = MyMessage.from_bits(bits)        # decode into new instance
   msg3 = MyMessage.from_bytes(data)       # decode from bytes into new instance