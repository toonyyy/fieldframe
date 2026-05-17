Declarative Message
===================

Demonstrates defining a single message by **subclassing**
:class:`~fieldframe.core.Message`. Fields are declared as class variables
and fieldframe assigns their names automatically from the attribute name —
no ``name=`` argument needed.

This is the recommended style for fixed, reusable message types.

`Download declarative_message.py <https://github.com/yourname/fieldframe/blob/main/examples/declarative_message.py>`_

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

Message definition
------------------

The message is defined by subclassing :class:`~fieldframe.core.Message`.
Every :class:`~fieldframe.frame.component.FrameComponent` declared as a
class variable is registered automatically:

.. literalinclude:: ../../../examples/declarative_message.py
   :language: python
   :start-after: # ---------------------------------------------------------------------------
   :end-before: # ---------------------------------------------------------------------------
   :lines: 1-40

ComputedField functions
-----------------------

Three compute functions are defined before the class. They receive the
full sibling field list at encode time:

.. literalinclude:: ../../../examples/declarative_message.py
   :language: python
   :start-after: # ComputedField functions -- defined before the class so they are in scope
   :end-before: # Declarative message definition
   :dedent: 0

Setting values
--------------

All three set styles work identically regardless of field type:

.. literalinclude:: ../../../examples/declarative_message.py
   :language: python
   :start-after: # Setting values -- all three styles work for regular fields
   :end-before: # Pretty print before encode
   :dedent: 0

Reading values
--------------

All read styles are shown after a decode round-trip:

.. literalinclude:: ../../../examples/declarative_message.py
   :language: python
   :start-after: # Reading values -- all styles
   :end-before: # Pretty print after decode
   :dedent: 0

Full source
-----------

.. literalinclude:: ../../../examples/declarative_message.py
   :language: python
   :caption: examples/declarative_message.py
   :linenos: