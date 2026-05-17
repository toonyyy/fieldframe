Declarative Protocol
====================

Demonstrates defining a full multi-message protocol by **subclassing**
:class:`~fieldframe.protocols.Protocol`. Nested ``Message`` classes named
``Header`` are picked up automatically. Any other nested ``Message`` subclass
with a ``_msg_id`` attribute is registered as a typed message under that key.

`Download declarative_protocol.py <https://github.com/yourname/fieldframe/blob/main/examples/declarative_protocol.py>`_

----

What this example covers
-------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 0

   * - Protocol subclassing
     - ``key=`` and ``name=`` class keywords
   * - Header auto-injection
     - Deep-copied and prepended to every registered message automatically
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

Protocol structure
------------------

The ``CarProtocol`` defines five message types. Every frame on the wire
follows this layout:

.. code-block:: text

    [ Header: msg_id(8)  ecu_id(8)  version(4) ]
    [ Payload: varies by message type           ]
    [ crc(8): XOR of all preceding int fields   ]

The header is prepended automatically by the protocol. The ``crc`` field
is the last ``ComputedField`` inside each message — because it runs after
all other fields have been encoded it sees the complete flattened field list
including the injected header fields, giving a true whole-frame check.

----

Protocol definition
-------------------

.. literalinclude:: ../../../examples/declarative_protocol.py
   :language: python
   :start-after: # Protocol definition -- declarative subclass style
   :end-before: # Instantiate -- one protocol instance for the whole application
   :dedent: 0

CRC design
----------

The ``frame_crc`` function is passed as the ``compute`` argument to a
:class:`~fieldframe.fields.compute.ComputedField` placed last in every
message. It skips the ``crc`` field itself and XORs every other integer
write value in the frame:

.. literalinclude:: ../../../examples/declarative_protocol.py
   :language: python
   :start-after: # ComputedField functions
   :end-before: # Protocol definition
   :dedent: 0

Encoding — always via the protocol's registered instance
---------------------------------------------------------

.. code-block:: python

   # CORRECT -- header already injected, crc sees the full frame
   bits = protocol.messages["1"].encode()

   # WRONG -- bare instance has no header, crc is incomplete
   bits = Heartbeat().encode()

Encode/decode round-trips
--------------------------

.. literalinclude:: ../../../examples/declarative_protocol.py
   :language: python
   :start-after: # Heartbeat -- encode via the protocol's registered instance
   :end-before: # Display -- pretty print all registered messages
   :dedent: 0

Full source
-----------

.. literalinclude:: ../../../examples/declarative_protocol.py
   :language: python
   :caption: examples/declarative_protocol.py
   :linenos: