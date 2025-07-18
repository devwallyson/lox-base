"""
Implementa o transformador da árvore sintática que converte entre as representações

    lark.Tree -> lox.ast.Node.

A resolução de vários exercícios requer a modificação ou implementação de vários
métodos desta classe.
"""

from typing import Callable
from lark import Transformer, v_args

from . import runtime as op
from .ast import *


def op_handler(op: Callable):
    """
    Fábrica de métodos que lidam com operações binárias na árvore sintática.

    Recebe a função que implementa a operação em tempo de execução.
    """

    def method(self, left, right):
        return BinOp(left, right, op)

    return method


@v_args(inline=True)
class LoxTransformer(Transformer):
    def program(self, *stmts):
        return Program(list(stmts))

    mul = op_handler(op.mul)
    div = op_handler(op.truediv)
    sub = op_handler(op.sub)
    add = op_handler(op.add)
    
    gt = op_handler(op.gt)
    lt = op_handler(op.lt)
    ge = op_handler(op.ge)
    le = op_handler(op.le)
    eq = op_handler(op.eq)
    ne = op_handler(op.ne)

    def call(self, func: Expr, params: list):
        return Call(func, params)
        
    def params(self, *args):
        params = list(args)
        return params

    def getattr(self, value, *attrs):
        for attr in attrs:
            value = Getattr(value, attr.name)
        return value

    def lvalue(self, expr, attr=None):
        if attr is not None:
            return Getattr(expr, attr.value)
        else:
            return expr

    def print_cmd(self, expr):
        return Print(expr)

    def VAR(self, token):
        name = str(token)
        return Var(name)

    def NUMBER(self, token):
        num = float(token)
        return Literal(num)
    
    def STRING(self, token):
        text = str(token)[1:-1]
        return Literal(text)
    
    def NIL(self, _):
        return Literal(None)

    def super(self, _):
        from .ast import Super
        return Super()
    
    def super_access(self, method_name):
        from .ast import Super
        return Super(method_name.name)
    
    def THIS(self, _):
        from .ast import This
        return This()

    def BOOL(self, token):
        return Literal(token == "true")

    def primary(self, child):
        return child

    def neg(self, expr):
        return UnaryOp(expr, op.neg)
    
    def not_(self, expr):
        return UnaryOp(expr, op.not_)
    
    def and_(self, left, right):
        return And(left, right)
    
    def or_(self, left, right):
        return Or(left, right)
    
    def assign(self, name, value):
        return Assign(name.name, value)
    
    def setattr_call(self, call_expr, attr, value):
        return Setattr(call_expr, attr.name, value)
    
    def setattr_getattr(self, getattr_expr, value):
        return Setattr(getattr_expr.value, getattr_expr.attr, value)
    
    def var_def_init(self, name, value):
        return VarDef(name.name, value)
    
    def var_def_no_init(self, name):
        return VarDef(name.name, Literal(None))
    
    def block(self, *stmts):
        return Block(list(stmts))
    
    def if_stmt(self, condition, then_stmt, else_stmt=None):
        return If(condition, then_stmt, else_stmt)
    
    def while_stmt(self, condition, body):
        return While(condition, body)
    
    def for_stmt(self, init, cond, incr, body):
        if cond is None:
            cond = Literal(True)
        if incr is not None:
            while_body = Block([body, incr])
        else:
            while_body = body
        while_loop = While(cond, while_body)
        if init is not None:
            return Block([init, while_loop])
        else:
            return while_loop
    
    def for_init(self, init=None):
        return init
    
    def for_cond(self, cond=None):
        return cond
    
    def for_incr(self, incr=None):
        return incr
    
    def fun_def(self, name, params, body):
        param_names = [param.name for param in params] if params else []
        return Function(name.name, param_names, body)
    
    def fun_params(self, *params):
        return list(params)
    
    def return_stmt(self, value=None):
        return Return(value)

    def class_def_simple(self, name, methods):
        return Class(name.name, methods)
    
    def class_def_inherit(self, name, superclass, methods):
        return Class(name.name, methods, superclass.name)
    
    def class_body(self, *methods):
        return list(methods)
    
    def method_def(self, name, params, body):
        param_names = [param.name for param in params] if params else []
        return Function(name.name, param_names, body)