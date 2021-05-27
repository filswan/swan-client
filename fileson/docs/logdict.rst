Logdict module
==============

With this simple class and its slice-ability you can do great things:

    >>> l = LogDict(a=1, b=2)
    >>> list(l.items())
    [('a', 1), ('b', 2)]
    >>> l['c'] = 3
    >>> l['b'] = 999
    >>> list(l.items())
    [('a', 1), ('b', 999), ('c', 3)]
    >>> l.log
    [('a', 1), ('b', 2), ('c', 3), ('b', 999)]
    >>> l2 = l.slice(('c', 3), None) # to the end
    >>> l2.log
    [('c', 3), ('b', 999)]
    >>> list(l2.items())
    [('c', 3), ('b', 999)]

Continuing from above, you can save the LogDict log to file:

    >>> l2.save('my.log')

A powerful additional feature is the append-only file (AOF) logging
that enables storing changes continuously to disk.

    >>> l = LogDict.load('my.log', logging=True)
    >>> list(l.items())
    [('c', 3), ('b', 999)]
    >>> l['x'] = 123 # immediately persisted to disk

.. automodule:: logdict
   :members:
