Pretty Printing
===============

Every field type and :class:`~fieldframe.core.Message` supports rich
box-drawn terminal display via ``print()`` or ``str()``. This is useful
for debugging, inspecting message state at the REPL, and building
human-readable logs.

Message
-------

``print(msg)`` renders a table showing every field's name, type, staged
write value, and last decoded read value. Nested sub-messages appear as a
summary row in the parent table, then rendered in full below it:

.. code-block:: python

   print(msg)

.. code-block:: text

   ┌─ Message: TelemetryMessage  (big-endian, 40 bits) ───────────┐
   │ name     │ type   │ write │ read │
   ├──────────┼────────┼───────┼──────┤
   │ speed    │ uint8  │ 120   │ 120  │
   │ altitude │ uint16 │ 1500  │ 1500 │
   │ heading  │ int16  │ -45   │ -45  │
   └──────────┴────────┴───────┴──────┘

Field
-----

``print(field)`` shows the field's name, type, default, staged write value,
and last decoded read value. ``—`` is shown for ``read`` until the field has
been decoded at least once:

.. code-block:: python

   print(msg.speed)

.. code-block:: text

   ┌─ Field ────────────────────────────┐
   │  name      speed                   │
   │  type      uint8                   │
   │  default   0                       │
   │  write     120                     │
   │  read      —                       │
   └────────────────────────────────────┘

FlagsField
----------

``print(flags_field)`` shows each flag name with a ✓ or ✗ indicator, the
type, and both the packed write and read integer values:

.. code-block:: python

   print(msg.flags)

.. code-block:: text

   ┌─ FlagsField ──────────────────────────────────────────────┐
   │  name      status                                          │
   │  type      uint8  (8-bit, lsb_first=False)                 │
   │  flags     [✓] armed   [✗] locked   [✗] error   [✓] ready │
   │  write     129   read=—                                    │
   └────────────────────────────────────────────────────────────┘

ScaledField
-----------

``print(scaled_field)`` shows the physical range, resolution, number of
steps, wire width, and both the logical and raw wire integer values for
write and read:

.. code-block:: python

   print(msg.temperature)

.. code-block:: text

   ┌─ ScaledField ──────────────────────────────┐
   │  name        temperature                   │
   │  range       [-40.0, 85.0]                 │
   │  resolution  0.1                           │
   │  steps       1250  (11-bit wire)           │
   │  write       25.0  (wire=650)              │
   │  read        —     (wire=—)                │
   └────────────────────────────────────────────┘

ComputedField
-------------

``print(computed_field)`` shows the compute function name, default, last
computed write value, and last decoded read value:

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

Protocol
--------

:meth:`~fieldframe.protocols.Protocol.display` prints the protocol name
followed by the full message table for every registered message type:

.. code-block:: python

   proto.display()

.. code-block:: text

   Protocol: MyProtocol
   ┌─ Message: TelemetryMessage  (big-endian, 24 bits) ──────────┐
   │ name     │ type   │ write │ read │
   ...
   ┌─ Message: CommandMessage  (big-endian, 16 bits) ────────────┐
   ...

repr vs str
-----------

Every type also provides a compact ``repr()`` for quick REPL inspection:

.. code-block:: python

   >>> msg.speed
   Field(speed, uint8, write=120, read=120)

   >>> msg.flags
   FlagsField(status, uint8, armed=✓ locked=✗ error=✗ ready=✓)

   >>> msg.temperature
   ScaledField(temperature, [-40.0, 85.0], res=0.1, 11-bit, write=25.0)

   >>> msg.checksum
   ComputedField(checksum, uint8, fn=xor_checksum, read=171)