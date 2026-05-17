fieldframe
==========

**fieldframe** is a Python library for defining, encoding, and decoding
structured binary messages — built for embedded systems, hardware protocols,
and any application where precise bit-level control matters.

.. code-block:: python

   from fieldframe import Message, Field, uint_type, int_type

   class TelemetryMessage(Message):
       speed    = Field(type=uint_type(8),  default=0)
       altitude = Field(type=uint_type(16), default=0)
       heading  = Field(type=int_type(16),  default=0)

   msg = TelemetryMessage()
   msg.speed.write    = 120
   msg.altitude.write = 1500
   msg.heading.write  = -45

   bits  = msg.encode()
   again = TelemetryMessage.from_bits(bits)
   print(again.read_values)
   # {'speed': 120, 'altitude': 1500, 'heading': -45}

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   guide/messages
   guide/field_types
   guide/flags
   guide/scaled
   guide/computed
   guide/protocols
   guide/byte_order
   guide/values
   guide/pretty_printing

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/message
   api/fields
   api/types
   api/protocols
   api/component

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/index

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog