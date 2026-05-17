Setting and Reading Values
==========================

fieldframe gives you several ways to get and set field values depending on
what is most convenient for your use case. All styles are equivalent on the
wire — they all ultimately read or write the same underlying ``write`` and
``read`` attributes.

----

Write side
----------

The write side is the value **staged for the next encode**. You set it
before calling :meth:`~fieldframe.core.Message.encode`.

Attribute access — ``field.write``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The most explicit style. Access the field by name on the message, then
assign to its ``write`` attribute. Validation runs immediately — an
out-of-range value raises :exc:`ValueError` at the point of assignment,
not silently at encode time:

.. code-block:: python

   msg.speed.write    = 120
   msg.altitude.write = 1500
   msg.heading.write  = -45   # signed fields accept negative values

Item access — ``msg['field'] = value``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Square bracket assignment on the message instance. Equivalent to
``msg.field.write = value`` — the same validation runs:

.. code-block:: python

   msg['speed']    = 120
   msg['altitude'] = 1500
   msg['heading']  = -45

Useful when the field name is held in a variable:

.. code-block:: python

   for name, value in updates.items():
       msg[name] = value

``msg.set(**kwargs)``
~~~~~~~~~~~~~~~~~~~~~

Set multiple fields at once using keyword arguments. Each key must be a
field name on the message:

.. code-block:: python

   msg.set(speed=120, altitude=1500, heading=-45)

Identical to calling ``msg['field'] = value`` for each pair. Useful for
compact one-liners when you know all the values up front.

Nested message access
~~~~~~~~~~~~~~~~~~~~~

For nested sub-messages, chain attribute access to reach the inner field:

.. code-block:: python

   msg.header.version.write = 2
   msg.header.msg_id.write  = 5

   # or item access into the sub-message
   msg['header']['version'] = 2

----

FlagsField — setting flags
--------------------------

:class:`~fieldframe.fields.flags.FlagsField` has additional access styles
because each bit is a named boolean rather than a single integer value.

Attribute access on the flags field:

.. code-block:: python

   msg.status.armed   = True
   msg.status.moving  = False

Item access on the flags field:

.. code-block:: python

   msg.status['armed']  = True
   msg.status['moving'] = False

Useful when the flag name is held in a variable:

.. code-block:: python

   for flag_name, flag_val in flag_updates.items():
       msg.status[flag_name] = flag_val

Check a flag's current write-side state:

.. code-block:: python

   if msg.status.armed:
       print("Armed!")

   if msg.status['armed']:
       print("Armed!")

----

Read side
---------

The read side is populated after a call to
:meth:`~fieldframe.core.Message.decode`,
:meth:`~fieldframe.core.Message.from_bits`, or
:meth:`~fieldframe.core.Message.from_bytes`. All read values are ``None``
until the message has been decoded at least once.

Single field — ``field.read``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   received = MyMessage.from_bits(bits)

   print(received.speed.read)     # 120
   print(received.altitude.read)  # 1500
   print(received.heading.read)   # -45

Single field via item access — ``msg['field'].read``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``msg['field']`` returns the field component itself, so ``.read`` works
the same way:

.. code-block:: python

   print(received['speed'].read)     # 120
   print(received['altitude'].read)  # 1500

All fields at once — ``msg.read_values``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns a ``{name: value}`` dictionary of every field's last decoded value.
This is the most common way to inspect a decoded message:

.. code-block:: python

   print(received.read_values)
   # {'speed': 120, 'altitude': 1500, 'heading': -45}

All write values — ``msg.write_values``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Returns a ``{name: value}`` dictionary of every field's current staged
write value. Useful for logging what you are about to send:

.. code-block:: python

   print(msg.write_values)
   # {'speed': 120, 'altitude': 1500, 'heading': -45}

.. note::

   For :class:`~fieldframe.fields.compute.ComputedField` (checksums,
   sequence numbers), ``write_values`` shows the value from the **previous**
   encode, not the one that will be computed on the next call. Capture
   ``write_values`` **after** calling ``encode()`` if you need the
   just-computed value:

   .. code-block:: python

      bits      = msg.encode()        # checksum / seq computed here
      sent_vals = msg.write_values    # now reflects the just-computed values

FlagsField reads
~~~~~~~~~~~~~~~~

After decode, read individual flags or the full flag state:

.. code-block:: python

   # Full decoded flag state as a dict
   print(received.status.flag_reads)
   # {'armed': True, 'moving': False, 'battery_low': False, ...}

   # Packed integer of the decoded state
   print(received.status.read)   # e.g. 144

   # Individual flag (returns write-side bool — use flag_reads for decoded)
   if received.status.armed:
       ...

ScaledField reads
~~~~~~~~~~~~~~~~~

:class:`~fieldframe.fields.scaled.ScaledField` exposes both the logical
float and the raw wire integer after decode:

.. code-block:: python

   print(received.temperature.read)      # 25.0  (logical float)
   print(received.temperature.read_raw)  # 650   (raw wire integer)

----

Quick reference
---------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Action
     - Syntax
   * - Set a field value
     - ``msg.speed.write = 120``
   * - Set via item access
     - ``msg['speed'] = 120``
   * - Set multiple fields at once
     - ``msg.set(speed=120, altitude=1500)``
   * - Set a flag
     - ``msg.status.armed = True``
   * - Set a flag via item access
     - ``msg.status['armed'] = True``
   * - Read last decoded value
     - ``msg.speed.read``
   * - Read via item access
     - ``msg['speed'].read``
   * - Read all decoded values
     - ``msg.read_values``
   * - Read all write values
     - ``msg.write_values``
   * - Read all decoded flags
     - ``msg.status.flag_reads``
   * - Read decoded flag packed int
     - ``msg.status.read``
   * - Read ScaledField raw wire int
     - ``msg.temperature.read_raw``