SMQTK Pending Release Notes
===========================

This document is currently a placeholder for tracking pending change / release
notes in between releases.


Updates / New Features
----------------------


Fixes
-----

CI

* Fix issues with typechecking caused by using more strict checks.

Misc.

* Minor fixes to package metadata files.

* Fixed issue with packages specifier in :file:`setup.py` where it was only
  excluding the top-level ``tests`` module but including the rest. Fixed to
  only explicitly include the ``smqtk_descriptors`` package and submodules.
