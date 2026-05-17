Changelog
=========

0.1.0 (2025)
------------

Initial release.

- :class:`~fieldframe.core.Message` — declarative and direct message definition
- :class:`~fieldframe.fields.field.Field` — fixed-width integer, float, and string fields
- :class:`~fieldframe.fields.flags.FlagsField` — named boolean flags packed into a single integer
- :class:`~fieldframe.fields.scaled.ScaledField` — float values stored as compact unsigned integers, auto-sized
- :class:`~fieldframe.fields.compute.ComputedField` — checksums and derived fields computed at encode time
- :class:`~fieldframe.protocols.Protocol` — multi-message protocol routing via a shared header key field
- Big and little endian support, configurable per message
- Bit reversal support for LSB-first transports
- Nested sub-messages
- Byte-boundary encode and decode via ``encode_bytes()`` / ``decode_bytes()``
- Pretty-printed terminal display for all field types and messages