"""
Implementa o transformador da árvore sintática que converte entre as representações

    lark.Tree -> lox.ast.Node.

A resolução de vários exercícios requer a modificação ou implementação de vários
métodos desta classe.
"""

from typing import Callable
from lark import Transformer, v_args
from dataclasses import dataclass  # <-- Adicione esta linha

from . import runtime as op
from .ast import (
    Program, BinOp, Var, Literal, And, Or, UnaryOp, Call, This, Super,
    Assign, Getattr, Setattr, Print, Return, VarDef, If, While, Block, Function, Class
)


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
    def start(self, program):
        return program

    def program(self, *stmts):
        return Program(list(stmts))

    def declaration(self, stmt):
        return stmt

    # Operações matemáticas básicas
    mul = op_handler(op.mul)
    div = op_handler(op.truediv)
    sub = op_handler(op.sub)
    add = op_handler(op.add)

    # Comparações
    gt = op_handler(op.gt)
    lt = op_handler(op.lt)
    ge = op_handler(op.ge)
    le = op_handler(op.le)
    eq = op_handler(op.eq)
    ne = op_handler(op.ne)

    # Outras expressões
    def call(self, obj, params: list):
        return Call(obj, params)
        
    def params(self, *args):
        params = list(args)
        return params
    
    def getatributo(self, value, *attrs):
        # attrs é uma tupla de Var
        for attr in attrs:
            value = Getattr(value, attr.name)
        return value

    def not_(self, value):
        return UnaryOp(op.not_, value)
    
    def neg(self, value):
        return UnaryOp(op.neg, value)
    
    def and_(self, left, right):
        return And(left, right)
    
    def or_(self, left, right):
        return Or(left, right)
    
    def assign(self, var, value):
        return Assign(var.name, value)
    
    def setattr(self, obj, value):
        return Setattr(obj.value, obj.attr, value)
    
    def block(self, *stmts):
        return Block(list(stmts))
    
    def if_cmd(self, cond, then_branch, else_branch=None):
        return If(cond, then_branch, else_branch)
    
    def while_cmd(self, expr, stmt):
        return While(expr, stmt)
    
    def var_dec(self, name, value=None):
        return VarDef(name.name, value)
    
    def for_init(self, *args):
        if len(args) == 0:
            return Literal(None)
        return args[0]

    def for_cond(self, *args):
        if len(args) == 0:
            return Literal(True)
        return args[0]

    def for_incr(self, *args):
        if len(args) == 0:
            return Literal(None)
        return args[0]

    def for_cmd(self, init, cond, incr, body):
        # init, cond, incr já são tratados pelas regras auxiliares
        # Se init é apenas um Literal(None), não adiciona ao bloco externo
        stmts = []
        if not (isinstance(init, Literal) and init.value is None):
            stmts.append(init)
        # Corpo do while
        while_stmts = []
        if isinstance(body, Block):
            while_stmts.extend(body.stmts)
        else:
            while_stmts.append(body)
        if not (isinstance(incr, Literal) and incr.value is None):
            while_stmts.append(incr)
        while_block = Block(while_stmts)
        while_stmt = While(cond, while_block)
        stmts.append(while_stmt)
        return Block(stmts)

    # Comandos
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

    def BOOL(self, token):
        return Literal(token == "true")
    
    def expr_stmt(self, expr):
        return expr

    def function_dec(self, name, *args):
        # args pode ser (body,) ou (params, body)
        if len(args) == 1:
            params = []
            body = args[0]
        elif len(args) == 2:
            params = args[0]
            body = args[1]
        else:
            raise ValueError("function_dec: argumentos inesperados")
        param_names = [v.name for v in params]
        return Function(name.name, param_names, body)

    def parameters(self, *vars):
        return list(vars)

    def return_cmd(self, expr=None):
        return Return(expr)