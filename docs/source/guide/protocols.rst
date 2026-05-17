Protocols
=========

:class:`~fieldframe.protocols.Protocol` is a high-level container that
groups a shared header, an optional footer, and a registry of message types.
It lets you decode an arbitrary incoming bitstream without knowing its type
in advance — the header is decoded first, a key field is read, and the
matching message type is selected automatically.

Declarative style
-----------------

The recommended way is to subclass :class:`~fieldframe.protocols.Protocol`
and nest your header, footer, and message classes inside it. Each message
class must define a ``_msg_id`` class attribute that is used as its registry
key:

.. code-block:: python

   from fieldframe import Message, Field, uint_type
   from fieldframe.protocols import Protocol

   class MyProtocol(Protocol, key="msg_id", name="MyProtocol"):

       class Header(Message):
           msg_id  = Field(type=uint_type(8), default=0)
           version = Field(type=uint_type(8), default=1)

       class TelemetryMessage(Message):
           _msg_id  = 1
           altitude = Field(type=uint_type(16), default=0)

       class CommandMessage(Message):
           _msg_id  = 2
           command  = Field(type=uint_type(8),  default=0)

   proto = MyProtocol()

The ``key`` class keyword argument names the field in the header that
identifies the message type. fieldframe automatically:

- Prepends a deep copy of the header to every registered message
- Stamps each message's embedded header with its own ``_msg_id`` value
- Builds a registry mapping key values to message instances

Direct instantiation
--------------------

For dynamic or one-off protocols, pass everything to the constructor:

.. code-block:: python

   proto = Protocol(
       name="MyProtocol",
       header=Header(),
       key="msg_id",
       messages={
           "1": TelemetryMessage(),
           "2": CommandMessage(),
       },
   )

Header and footer
-----------------

The **header** is required and must contain the key field. A deep copy of
it is prepended to every registered message automatically.

The **footer** is optional. When provided, a deep copy is appended to every
registered message:

.. code-block:: python

   class MyProtocol(Protocol, key="msg_id"):

       class Header(Message):
           msg_id = Field(type=uint_type(8), default=0)

       class Footer(Message):
           crc = Field(type=uint_type(16), default=0)

       class DataMessage(Message):
           _msg_id = 1
           value   = Field(type=uint_type(16), default=0)

Neither header nor footer can be changed after the protocol is initialised.

Decoding
--------

Pass a complete bitstream to :meth:`~fieldframe.protocols.Protocol.decode`.
The protocol decodes the header slice first, extracts the key field value,
looks up the matching message, and decodes the full bitstream against it:

.. code-block:: python

   result = proto.decode(incoming_bits)
   # Returns the read_values dict from the matched message

If the key value is not found in the registry, :exc:`KeyError` is raised.

Managing messages at runtime
-----------------------------

Messages can be added to or removed from the registry after construction:

.. code-block:: python

   proto.add_message("3", DiagnosticsMessage())
   proto.remove_message("3")

   # Look up a message by its name attribute (not key)
   msg = proto.get_message("TelemetryMessage")

Displaying a protocol
---------------------

:meth:`~fieldframe.protocols.Protocol.display` prints the protocol name
followed by the full pretty-printed table for every registered message:

.. code-block:: python

   proto.display()

.. code-block:: text

   Protocol: MyProtocol
   ┌─ Message: TelemetryMessage  (big-endian, 24 bits) ──────────┐
   │ name     │ type   │ write │ read │
   ...
   ┌─ Message: CommandMessage  (big-endian, 16 bits) ────────────┐
   ...