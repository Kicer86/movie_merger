
import inspect
import os
import shutil
import tempfile


class TestDataWorkingDirectory:
    def __init__(self):
        self.directory = None

    @property
    def path(self):
        return self.directory

    def __enter__(self):
        self.directory = os.path.join(tempfile.gettempdir(), "twotone_tests", inspect.stack()[1].function)
        if os.path.exists(self.directory):
            shutil.rmtree(self.directory)

        os.makedirs(self.directory, exist_ok=True)
        return self

    def __exit__(self, type, value, traceback):
        shutil.rmtree(self.directory)
