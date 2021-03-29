SMQTK Pending Release Notes
===========================

This document is currently a placeholder for tracking pending change / release
notes in between releases.


Updates / New Features
----------------------

Misc.

* Now standardize to using `Poetry`_ for environment/build/publish management.

  * Collapsed pytest configuration into the :file:`pyproject.toml` file.

Fixes
-----

CI

* Remove a debug command in a GitHub CI workflow job.

* Fix some LGTM warnings.

* Update CI configurations to use `Poetry`_.


.. _Poetry: https://python-poetry.org/
