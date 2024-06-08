from typing import Final, Tuple, Dict, Union


class Extension:
    def __init__(self, client, pkg, **kwargs):
        self.depends: Final[Tuple[str]] = kwargs.get("depends", ())
        self.provides: Final[Tuple[str]] = kwargs.get("provides", ())
        self.interfaces: Dict[str, Union[Extension, None]] = {}
        self.name: str = kwargs.get("name", self.__class__.__name__)
        self.importby: str = pkg
        self.client = client

    async def teardown(self):
        """
        Method called before the module is unloaded so that it may do internal unloading
        """
        pass
