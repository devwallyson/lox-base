import builtins
from dataclasses import dataclass
from operator import neg
from typing import TYPE_CHECKING, Optional
from types import FunctionType, BuiltinFunctionType

from .ctx import Ctx

if TYPE_CHECKING:
    from .ast import Stmt, Value, Block, Function


class LoxError(Exception):
    """
    Exceção para erros em tempo de execução do Lox.
    """
    pass


@dataclass
class LoxClass:
    """
    Classe base para todas as classes Lox.
    """
    name: str
    methods: dict[str, "LoxFunction"]
    base: Optional["LoxClass"] = None
    
    def __call__(self, *args):
        instance = LoxInstance(self)
        
        try:
            init_method = self.get_method("init")
            bound_init = init_method.bind(instance)
            bound_init(*args)
        except LoxError:
            if args:
                raise LoxError(f"Expected 0 arguments but got {len(args)}.")
            pass
        
        return instance
    
    def get_method(self, name: str) -> "LoxFunction":
        """
        Procura o método na classe atual.
        Se não encontrar, procura nas bases.
        Se não existir em nenhum dos dois lugares, levanta uma exceção LoxError.
        """
        if name in self.methods:
            return self.methods[name]
        
        if self.base is not None:
            return self.base.get_method(name)
        
        raise LoxError(f"Undefined method '{name}'.")
    
    def __str__(self):
        return self.name


@dataclass
class LoxInstance:
    """
    Instância de uma classe Lox.
    """
    
    def __init__(self, lox_class):
        self.__class = lox_class
    
    def __str__(self):
        return f"{self.__class.name} instance"
    
    def __getattr__(self, attr):
        """
        Busca métodos na classe quando o atributo não existe na instância.
        """
        method = self.__class.get_method(attr)
        if method:
            if attr == "init":
                return self._create_init_wrapper(method)
            else:
                return LoxBoundMethod(self, method)
        else:
            raise AttributeError(f"'{self.__class.name}' object has no attribute '{attr}'")
    
    def _create_init_wrapper(self, init_method):
        """
        Cria um wrapper para o método init que sempre retorna this.
        """
        def init_wrapper(*args):
            bound_init = init_method.bind(self)
            bound_init(*args)  
            return self  
        return init_wrapper


class LoxBoundMethod:
    """
    Método vinculado a uma instância.
    """
    def __init__(self, instance: "LoxInstance", method: "LoxFunction"):
        self.instance = instance
        self.method = method
        from .ctx import Ctx
        self.bound_ctx = Ctx({"this": instance})
    
    def __call__(self, *args):
        if len(args) != len(self.method.params):
            raise LoxError(f"Expected {len(self.method.params)} arguments but got {len(args)}.")
        
        from .ctx import Ctx
        env = {"this": self.instance}
        for i, param in enumerate(self.method.params):
            if i < len(args):
                env[param] = args[i]
        
        new_ctx = self.method.ctx.push(env)
        try:
            self.method.body.eval(new_ctx)
            return None
        except LoxReturn as e:
            return e.value
    
    def __str__(self):
        return f"<fn {self.method.name}>"
    
    def __eq__(self, other):
        return self is other
    
    def __hash__(self):
        return id(self)


class LoxReturn(Exception):
    """
    Exceção para retornar de uma função Lox.
    """

    def __init__(self, value):
        self.value = value
        super().__init__()


class SuperProxy:
    """
    Proxy para acesso a métodos da superclasse.
    """
    
    def __init__(self, superclass, instance):
        self.__superclass = superclass
        self.__instance = instance
    
    def __getattr__(self, attr):
        """
        Busca métodos na superclasse quando o atributo é acessado.
        """
        method = self.__superclass.get_method(attr)
        if method:
            return method.bind(self.__instance)
        else:
            raise AttributeError(f"'{self.__superclass.name}' object has no attribute '{attr}'")


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
    if value is None:
        return "nil"
    elif value is True:
        return "true"
    elif value is False:
        return "false"
    elif isinstance(value, str):
        return value 
    elif isinstance(value, float):
        if value == 0.0 and str(value) == "-0.0":
            return "-0"
        elif value.is_integer():
            return str(int(value))
        return str(value)
    elif isinstance(value, LoxClass):
        return str(value)  
    elif isinstance(value, LoxInstance):
        return str(value) 
    elif isinstance(value, LoxBoundMethod):
        return str(value)  
    elif isinstance(value, LoxFunction):
        return str(value)  
    elif isinstance(value, (FunctionType, BuiltinFunctionType)):
        return "<native fn>"
    elif isinstance(value, type):
        return value.__name__
    elif hasattr(value, "__class__") and hasattr(value.__class__, "__name__"):
        return f"{value.__class__.__name__} instance"
    else:
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


def add(left: "Value", right: "Value") -> "Value":
    """
    Soma dois valores: números ou strings.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be two numbers or two strings.")
    
    if isinstance(left, str) and isinstance(right, str):
        return left + right
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left + right
    
    raise LoxError("Operands must be two numbers or two strings.")


def sub(left: "Value", right: "Value") -> "Value":
    """
    Subtrai dois números.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left - right
    
    raise LoxError("Operands must be numbers.")


def mul(left: "Value", right: "Value") -> "Value":
    """
    Multiplica dois números.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left * right
    
    raise LoxError("Operands must be numbers.")


def truediv(left: "Value", right: "Value") -> "Value":
    """
    Divide dois números.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left / right if right != 0 else float('nan')
    
    raise LoxError("Operands must be numbers.")


def gt(left: "Value", right: "Value") -> bool:
    """
    Verifica se left > right (apenas números).
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left > right
    
    raise LoxError("Operands must be numbers.")


def ge(left: "Value", right: "Value") -> bool:
    """
    Verifica se left >= right (apenas números).
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left >= right
    
    raise LoxError("Operands must be numbers.")


def lt(left: "Value", right: "Value") -> bool:
    """
    Verifica se left < right (apenas números).
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left < right
    
    raise LoxError("Operands must be numbers.")


def le(left: "Value", right: "Value") -> bool:
    """
    Verifica se left <= right (apenas números).
    """
    if isinstance(left, bool) or isinstance(right, bool):
        raise LoxError("Operands must be numbers.")
    
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left <= right
    
    raise LoxError("Operands must be numbers.")


def eq(left: "Value", right: "Value") -> bool:
    """
    Verifica igualdade estrita (sem conversão de tipos).
    """
    if type(left) != type(right):
        return False
    
    return left == right


def ne(left: "Value", right: "Value") -> bool:
    """
    Verifica desigualdade estrita.
    """
    return not eq(left, right)


def not_(value: "Value") -> bool:
    """
    Operador NOT com semântica do Lox.
    """
    return not truthy(value)


@dataclass
@dataclass
class LoxFunction:
    """
    Classe base para todas as funções Lox.
    """

    name: str
    params: list[str]
    body: "Block"
    ctx: Ctx

    def __call__(self, *args):
        if len(args) != len(self.params):
            raise LoxError(f"Expected {len(self.params)} arguments but got {len(args)}.")
        
        env = dict(zip(self.params, args, strict=True))
        new_ctx = self.ctx.push(env)

        try:
            self.body.eval(new_ctx)
            return None
        except LoxReturn as e:
            return e.value
    
    def bind(self, obj: "Value") -> "LoxFunction":
        """
        Associa essa função a um this específico, criando uma nova função
        com um contexto que inclui {"this": obj}.
        """
        return LoxFunction(
            name=self.name,
            params=self.params,
            body=self.body,
            ctx=self.ctx.push({"this": obj})
        )

    def __str__(self):
        return f"<fn {self.name}>"