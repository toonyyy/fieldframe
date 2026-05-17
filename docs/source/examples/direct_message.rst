Direct Message
==============

Demonstrates defining a single message by passing a **field list directly**
to the :class:`~fieldframe.core.Message` constructor — no subclassing
required. Every field must be given an explicit ``name=`` argument because
there is no class body for fieldframe to read attribute names from.

This style is better suited for messages built at runtime or from
configuration data where the structure is not known at import time.

`Download direct_message.py <https://github.com/yourname/fieldframe/blob/main/examples/direct_message.py>`_

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

Declarative vs direct — the only difference
--------------------------------------------

Both examples define an identical ``VehicleData`` message and perform the
same operations. The only difference is how the message is constructed:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Declarative
     - Direct
   * - ``class VehicleData(Message):``
     - ``msg = Message("VehicleData", [...])``
   * - Field names inferred from attribute names
     - Field names must be passed as ``name=``
   * - Supports ``from_bits()`` / ``from_bytes()``
     - Encode/decode only via instance methods
   * - Best for fixed, reusable types
     - Best for runtime or config-driven construction

----

Message construction
--------------------

The message is built by passing a list of field instances to the
:class:`~fieldframe.core.Message` constructor:

.. literalinclude:: ../../../examples/direct_message.py
   :language: python
   :start-after: # Direct instantiation -- field list passed to constructor
   :end-before: # Setting values
   :dedent: 0

Setting values
--------------

The set styles are identical to the declarative example:

.. literalinclude:: ../../../examples/direct_message.py
   :language: python
   :start-after: # Setting values -- all three styles work identically to the declarative style
   :end-before: # Pretty print before encode
   :dedent: 0

Reading values
--------------

.. literalinclude:: ../../../examples/direct_message.py
   :language: python
   :start-after: # Reading values -- all styles
   :end-before: # Pretty print after decode
   :dedent: 0

Full source
-----------

.. literalinclude:: ../../../examples/direct_message.py
   :language: python
   :caption: examples/direct_message.py
   :linenos: