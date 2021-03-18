DataProvider
----------------

An important part of any algorithm is the data its working over and the data that it produces.
An important part of working with large scales of data is where the data is stored and how its accessed.
The ``smqtk_dataprovider`` module contains interfaces and plugins for various core data structures, allowing plugin implementations to decide where and how the underlying raw data should be stored and accessed.
This potentially allows algorithms to handle more data that would otherwise be feasible on a single machine.


DataProvider Structures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following are the core data representation interfaces.

Note:
  It is required that implementations have a common serialization format so that they may be stored or transported by other structures in a general way without caring what the specific implementation is.
  For this we require that all implementations be serializable via the ``pickle`` (and thus ``cPickle``) module functions.

DataElement
+++++++++++

.. autoclass:: smqtk_dataprovider.DataElement
   :members:

DataSet
+++++++

.. autoclass:: smqtk_dataprovider.DataSet
   :members:

KeyValueStore
+++++++++++++

.. autoclass:: smqtk_dataprovider.KeyValueStore
   :members:
