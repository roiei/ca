import abc
import typing


class Cmd(abc.ABC):
    @abc.abstractmethod
    def execute(self, opts: typing.Dict, cfg) -> bool:
        ...
