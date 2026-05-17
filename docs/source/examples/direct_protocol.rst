Direct Protocol
===============

Demonstrates defining a full multi-message protocol by passing message
instances **directly to the** :class:`~fieldframe.protocols.Protocol`
**constructor** — no subclassing required. Every message and the header are
constructed as ``Message("name", [...])`` instances and passed in. The
protocol still automatically prepends the header and stamps each message's
key field value.

`Download direct_protocol.py <https://github.com/yourname/fieldframe/blob/main/examples/direct_protocol.py>`_

----

What this example covers
-------------------------

.. list-table::
   :widths: 30 70
   :header-rows: 0

   * - Protocol direct instantiation
     - ``name=``, ``header=``, ``key=``, ``messages=`` constructor arguments
   * - Header as a plain Message instance
     - Constructed with ``Message("Header", [...])`` and passed to ``header=``
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

Declarative vs direct protocols — the only difference
------------------------------------------------------

Both protocol examples define an identical ``CarProtocol`` with the same
five messages and perform the same encode/decode round-trips. The only
difference is construction syntax:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Declarative
     - Direct
   * - ``class CarProtocol(Protocol, key="msg_id"):``
     - ``protocol = Protocol(name=..., header=..., key=..., messages=...)``
   * - Nested ``class Header(Message):``
     - ``header = Message("Header", [...])``
   * - Nested ``class Heartbeat(Message):`` with ``_msg_id = "1"``
     - ``heartbeat = Message("Heartbeat", [...])`` passed under key ``"1"``
   * - Best for fixed protocols known at import time
     - Best for protocols built at runtime or from configuration

----

Protocol structure
------------------

Every frame on the wire follows this layout regardless of construction style:

.. code-block:: text

    [ Header: msg_id(8)  ecu_id(8)  version(4) ]
    [ Payload: varies by message type           ]
    [ crc(8): XOR of all preceding int fields   ]

----

Building the header and messages
---------------------------------

.. literalinclude:: ../../../examples/direct_protocol.py
   :language: python
   :start-after: # Build all message instances directly
   :end-before: # Instantiate the protocol directly
   :dedent: 0

Instantiating the protocol
---------------------------

.. literalinclude:: ../../../examples/direct_protocol.py
   :language: python
   :start-after: # Instantiate the protocol directly
   :end-before: # Heartbeat -- encode via the protocol's registered instance
   :dedent: 0

Encoding — always via the protocol's registered instance
---------------------------------------------------------

.. code-block:: python

   # CORRECT -- header already injected, crc sees the full frame
   bits = protocol.messages["1"].encode()

   # WRONG -- bare instance has no header, crc is incomplete
   bits = heartbeat.encode()

Encode/decode round-trips
--------------------------

.. literalinclude:: ../../../examples/direct_protocol.py
   :language: python
   :start-after: # Heartbeat -- encode via the protocol's registered instance
   :end-before: # Display -- pretty print all registered messages
   :dedent: 0

Full source
-----------

.. literalinclude:: ../../../examples/direct_protocol.py
   :language: python
   :caption: examples/direct_protocol.py
   :linenos: