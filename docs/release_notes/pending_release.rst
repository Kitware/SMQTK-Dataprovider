Pending Release Notes
=====================

Updates / New Features
----------------------

* Added Python 3.14 support and testing for all optional dependency configurations.

* Required SMQTK-Core 0.22.0, which officially supports Python 3.14.

* Allowed NumPy 2 on Python 3.10–3.12 while retaining NumPy 1 compatibility.
  Set minimum NumPy versions on Python 3.13 and 3.14 to releases that provide
  wheels for those interpreters.

Fixes
-----

* Used Amazon ECR Public's mirror of Docker's official Python images in CI to
  avoid Docker Hub's unauthenticated pull rate limit.

* Updated Girder client so the optional Girder integration remains usable in
  current Python environments.
  Girder tests now fail on broken client imports instead of silently skipping.

* Updated vulnerable dependencies to patched releases and raised the declared
  Requests, IPython, and pytest minimums.
