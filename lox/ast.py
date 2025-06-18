from abc import ABC
from dataclasses import dataclass
from typing import Callable

from .ctx import Ctx
from .runtime import LoxFunction, LoxReturn

# Declaramos nossa classe base num módulo separado para esconder um pouco de
# Python relativamente avançado de quem não se interessar pelo assunto.
#
# A classe Node implementa um método `pretty` que imprime as árvores de forma
# legível. Também possui funcionalidades para navegar na árvore usando cursores
# e métodos de visitação.
from .node import Node


#
# TIPOS BÁSICOS
#

# Tipos de valores que podem aparecer durante a execução do programa
Value = bool | str | float | None


class Expr(Node, ABC):
    """
    Classe base para expressões.

    Expressões são nós que podem ser avaliados para produzir um valor.
    Também podem ser atribuídos a variáveis, passados como argumentos para
    funções, etc.
    """


class Stmt(Node, ABC):
    """
    Classe base para comandos.

    Comandos são associdos a construtos sintáticos que alteram o fluxo de
    execução do código ou declaram elementos como classes, funções, etc.
    """


@dataclass
class Program(Node):
    """
    Representa um programa.

    Um programa é uma lista de comandos.
    """

    stmts: list[Stmt]

    def eval(self, ctx: Ctx):
        for stmt in self.stmts:
            stmt.eval(ctx)


#
# EXPRESSÕES
#
@dataclass
class BinOp(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x + y, 2 * x, 3.14 > 3 and 3.14 < 4
    """

    left: Expr
    right: Expr
    op: Callable[[Value, Value], Value]

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        right_value = self.right.eval(ctx)
        return self.op(left_value, right_value)


@dataclass
class Var(Expr):
    """
    Uma variável no código

    Ex.: x, y, z
    """

    name: str

    def eval(self, ctx: Ctx):
        try:
            return ctx[self.name]
        except KeyError:
            raise NameError(f"variável {self.name} não existe!")


@dataclass
class Literal(Expr):
    """
    Representa valores literais no código, ex.: strings, booleanos,
    números, etc.

    Ex.: "Hello, world!", 42, 3.14, true, nil
    """

    value: Value

    def eval(self, ctx: Ctx):
        return self.value


def is_truthy(value):
    return not (value is False or value is None)

@dataclass
class And(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x and y
    """
    left: Expr
    right: Expr

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        if not is_truthy(left_value):
            return left_value
        return self.right.eval(ctx)


@dataclass
class Or(Expr):
    """
    Uma operação infixa com dois operandos.
    Ex.: x or y
    """
    left: Expr
    right: Expr

    def eval(self, ctx: Ctx):
        left_value = self.left.eval(ctx)
        if is_truthy(left_value):
            return left_value
        return self.right.eval(ctx)

@dataclass
class UnaryOp(Expr):
    """
    Uma operação prefixa com um operando.

    Ex.: -x, !x
    """
    op: Callable
    value: Expr

    def eval(self, ctx: Ctx):
        v = self.value.eval(ctx)
        return self.op(v)


@dataclass
class Call(Expr):
    """
    Uma chamada de função.

    Ex.: fat(42)
    """
    obj: Expr
    params: list[Expr]
    
    def eval(self, ctx: Ctx):
        obj = self.obj.eval(ctx)
        params = [param.eval(ctx) for param in self.params]
        
        if callable(obj):
            return obj(*params)
        raise TypeError(f"{self.name} não é uma função!")


@dataclass
class This(Expr):
    """
    Acesso ao `this`.

    Ex.: this
    """


@dataclass
class Super(Expr):
    """
    Acesso a method ou atributo da superclasse.

    Ex.: super.x
    """


@dataclass
class Assign(Expr):
    """
    Atribuição de variável.

    Ex.: x = 42
    """
    name: str
    value: Expr

    def eval(self, ctx: Ctx):
        v = self.value.eval(ctx)
        ctx[self.name] = v
        return v


@dataclass
class Getattr(Expr):
    """
    Acesso a atributo de um objeto.

    Ex.: x.y
    """
    value: Expr
    attr: str

    def eval(self, ctx):
        obj = self.value.eval(ctx)
        return getattr(obj, self.attr)
        

@dataclass
class Setattr(Expr):
    """
    Atribuição de atributo de um objeto.

    Ex.: x.y = 42
    """
    obj: Expr
    attr: str
    value: Expr

    def eval(self, ctx: Ctx):
        obj = self.obj.eval(ctx)
        v = self.value.eval(ctx)
        setattr(obj, self.attr, v)
        return v


#
# COMANDOS
#
@dataclass
class Print(Stmt):
    """
    Representa uma instrução de impressão.

    Ex.: print "Hello, world!";
    """
    expr: Expr
    
    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx)
        # Conversão para o formato Lox
        if value is True:
            print("true")
        elif value is False:
            print("false")
        elif value is None:
            print("nil")
        elif isinstance(value, float) and value.is_integer():
            print(int(value))
        else:
            print(value)


@dataclass
class Return(Stmt):
    """
    Representa uma instrução de retorno.

    Ex.: return x;
    """
    expr: Expr = None

    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx) if self.expr else None
        raise LoxReturn(value)


@dataclass
class VarDef(Stmt):
    """
    Representa uma declaração de variável.

    Ex.: var x = 42;
    """

    name: str
    value: Expr | None = None

    def eval(self, ctx: Ctx):
        if self.value is not None:
            val = self.value.eval(ctx)
        else:
            val = None
        ctx.var_def(self.name, val)


@dataclass
class If(Stmt):
    """
    Representa uma instrução condicional.

    Ex.: if (x > 0) { ... } else { ... }
    """
    cond: Expr
    then_branch: Stmt
    else_branch: Stmt | None = None

    def eval(self, ctx:Ctx):
        if self.cond.eval(ctx):
            return self.then_branch.eval(ctx)
        elif self.else_branch is not None:
            return self.else_branch.eval(ctx)



@dataclass
class While(Stmt):
    """
    Representa um laço de repetição.

    Ex.: while (x > 0) { ... }
    """
    expr: Expr
    stmt: Stmt

    def eval(self, ctx: Ctx):
        while bool(self.expr.eval(ctx)):
            self.stmt.eval(ctx)



@dataclass
class Block(Node):
    """
    Representa bloco de comandos.

    Ex.: { var x = 42; print x;  }
    """
    stmts: list[Stmt]

    def eval(self, ctx:Ctx):
        ctx = ctx.push({})
        try:
            for stmt in self.stmts:
                stmt.eval(ctx)
        finally:
            ctx = ctx.pop()[1]


@dataclass
class Function(Stmt):
    """
    Representa uma função.

    Ex.: fun f(x, y) { ... }
    """
    name: str
    params: list[str]
    body: Block

    def eval(self, ctx: Ctx):
        fn = LoxFunction(self.name, self.params, self.body, ctx)
        ctx.var_def(self.name, fn)
        return fn


@dataclass
class Class(Stmt):
    """
    Representa uma classe.

    Ex.: class B < A { ... }
    """