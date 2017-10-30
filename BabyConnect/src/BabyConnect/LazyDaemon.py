import time
import os
from importlib import reload


# Simple watchdog class to check for changes in source to reload the module file as needed
class Watchdog:
    def __init__(self, module):
        self._module = module
        self._filename = module.__file__
        self._modified = self._get_mod_time()

    def _get_mod_time(self):
        return os.stat(self._filename).st_mtime

    def has_changed(self):
        modTime = self._get_mod_time()
        if modTime > self._modified:
            self._modified = modTime
            return True

    def check(self):
        if self.has_changed():
            print ("File change detected in \'{}\'...reloading...".format(self._module.__name__))
            reload(self._module)
