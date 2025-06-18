import builtins
from dataclasses import dataclass
from operator import add, eq, ge, gt, le, lt, mul, ne, neg, not_, sub, truediv
from typing import TYPE_CHECKING

from .ctx import Ctx

class LoxReturn(Exception):
    def __init__(self, value):
        super().__init__()
        self.value = value

@dataclass
class LoxFunction:
    name: str
    params: list[str]
    body: object  # Block
    ctx: Ctx

    def call(self, args):
        # Checa aridade
        if len(args) != len(self.params):
            raise RuntimeError(f"Expected {len(self.params)} arguments but got {len(args)}.")
        local_ctx = self.ctx.push({})
        try:
            for param, arg in zip(self.params, args):
                local_ctx.var_def(param, arg)
            try:
                self.body.eval(local_ctx)
            except LoxReturn as ex:
                return ex.value
        finally:
            local_ctx = local_ctx.pop()[1]

    def __call__(self, *args):
        return self.call(args)


nan = float("nan")
inf = float("inf")


def print(value: "Value"):
    """
    Imprime um valor lox.
    """
    builtins.print(show(value))


def show(value: "Value") -> str:
    """
    Converte valor lox para string.
    """
    return str(value)


def show_repr(value: "Value") -> str:
    """
    Mostra um valor lox, mas coloca aspas em strings.
    """
    if isinstance(value, str):
        return f'"{value}"'
    return show(value)


def truthy(value: "Value") -> bool:
    """
    Converte valor lox para booleano segundo a semântica do lox.
    """
    if value is None or value is False:
        return False
    return True