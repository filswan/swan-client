"""LogDict class with JSON log storage format and simple versioning."""

import json, os
from collections.abc import MutableMapping
from typing import Any, Tuple

class LogDict(MutableMapping):
    """Map-like object with append-only-file logging for persistence.

    All set and delete operations are written to append-only log and saved
    either real-time or upon request in line-based JSON format. Special
    version key and :meth:`slice` can be used to implement versioning.

    See :class:`collections.abc.MutableMapping` for interface details.

    Returns:
        LogDict: A class instance.
    """

    @classmethod
    def load(cls, filename: str, logging: bool=False) -> 'LogDict':
        """Create a LogDict, init from file and optionally start logging.

        Args:
            filename (str): Filename, read into object if exists
            logging (bool): Set to True to have append-only file log,
                or to False to explicitly :meth:`save` contents.

        Returns:
            LogDict: A new object
        """
        ld = cls()
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf8') as fin:
                for l in fin.readlines():
                    t = json.loads(l)
                    if len(t)==2: ld[t[0]] = t[1]
                    else: del ld[t[0]]
        if logging: ld.startLogging(filename)
        return ld

    def __init__(self, *args, **kwargs):
        self.__d = dict() # dict backend
        self.log = list() # log of operations
        self.__logfile = None
        self.update(dict(*args, **kwargs)) # use supplied update to init

    def startLogging(self, filename: str) -> None:
        """Start AOF logging.

        Args:
            filename (str): File to write to
        Raises:
            RuntimeError: If already logging
        """
        if self.__logfile: raise RuntimeError('Already logging!')
        self.__logfile = open(filename, 'a', encoding='utf8', buffering=1)

    def endLogging(self) -> None:
        """End AOF logging.

        Raises:
            RuntimeError: If not logging
        """
        if not self.__logfile: raise RuntimeError('Not logging!')
        self.__logfile.close()

    def save(self, filename: str) -> None:
        """Save log to file.

        Use :meth:`create` to restore from a saved log.

        Args:
            filename (str): File to write to
        """
        with open(filename, 'w', encoding='utf8') as fout:
            for t in self.log:
                json.dump(t, fout)
                fout.write('\n')

    def __del__(self):
        if self.__logfile: self.endLogging()

    def __setitem__(self, key, value):
        self.log.append((key, value)) # tuple for set
        if self.__logfile:
            json.dump((key, value), self.__logfile)
            self.__logfile.write('\n')
        self.__d[key] = value

    def __delitem__(self, key):
        self.log.append((key,)) # single item tuple for del
        if self.__logfile:
            json.dump((key,), self.__logfile)
            self.__logfile.write('\n')
        del self.__d[key]

    def slice(self, start: Tuple[Any, Any]=None,
            end: Tuple[Any, Any]=None) -> 'LogDict':
        """Create a new LogDict from a slice of operations log.

        As all mutations are logged, you can easily use key changes
        are markers to construct a partial LogDict. Just specify
        beginning and end (or None to use log start/end). Deleting
        non-existing nodes is automatically skipped.

        Args:
            start (tuple): A (key,value) pair for set, (key,) for del or None
            end (tuple): A (key,value) pair for set, (key,) for del or None

        Returns:
            LogDict: A copy with slice of the log and appropriate content.
        """
        ld = self.__class__() # make work with children
        i1 = self.log.index(start) if start else 0
        i2 = self.log.index(end) if end else len(self.log)
        for t in self.log[i1:i2]:
            if len(t)==2: ld[t[0]] = t[1]
            elif t[0] in ld: del ld[t[0]]
        return ld

    def __getitem__(self, key): return self.__d[key]
    def __iter__(self): return iter(self.__d)
    def __len__(self): return len(self.__d)
