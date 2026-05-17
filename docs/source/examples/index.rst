Examples
========

These examples demonstrate the full fieldframe API using a realistic
automotive protocol. Each example is a standalone runnable Python script
located in the ``examples/`` folder of the repository.

All four examples use the same field types, access patterns, and
encode/decode round-trips — the only difference is the construction style
(declarative subclassing vs direct instantiation) and the scope
(single message vs full protocol).

.. toctree::
   :maxdepth: 1
   :caption: Examples

   declarative_message
   direct_message
   declarative_protocol
   direct_protocol