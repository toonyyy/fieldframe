Installation
============

Requirements
------------

- Python 3.10 or later
- `bitarray <https://github.com/ilanschnell/bitarray>`_ >= 3.8.1

Installing from PyPI
--------------------

.. code-block:: bash

   pip install fieldframe

Installing for development
--------------------------

Clone the repository and install in editable mode with the development
and documentation extras:

.. code-block:: bash

   git clone https://github.com/yourname/fieldframe.git
   cd fieldframe
   pip install -e ".[dev,docs]"

The ``dev`` extra installs ``pytest`` and ``bitarray`` for running the test
suite.  The ``docs`` extra installs ``sphinx`` and ``furo`` for building
these pages locally.

Building the docs locally
--------------------------

.. code-block:: bash

   cd docs
   make html

The generated site will be in ``docs/build/html/``.  Open
``docs/build/html/index.html`` in your browser to preview it.