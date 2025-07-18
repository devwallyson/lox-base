from abc import ABC
from dataclasses import dataclass
from typing import Callable

from .ctx import Ctx
from .errors import SemanticError
from .node import Node, Cursor

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
    
    def validate_self(self, cursor: Cursor):
        reserved_words = {"true", "false", "nil", "return", "var", "fun", "class", "if", "else", "while", "for", "print", "and", "or", "this", "super"}
        
        if self.name in reserved_words:
            raise SemanticError("Expect variable name.", token=self.name)
        
        for parent_cursor in cursor.parents():
            if isinstance(parent_cursor.node, VarDef):
                if parent_cursor.node.name == self.name:
                    is_local = False
                    for ancestor in parent_cursor.parents():
                        if isinstance(ancestor.node, Block):
                            is_local = True
                            break
                    
                    if is_local:
                        raise SemanticError("Can't read local variable in its own initializer.", token=self.name)
                break


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


@dataclass
class And(Expr):
    """
    Uma operação infixa com dois operandos.

    Ex.: x and y
    """
    left: Expr
    right: Expr
    
    def eval(self, ctx: Ctx):
        left_val = self.left.eval(ctx)
        if left_val is False or left_val is None:
            return left_val
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
        left_val = self.left.eval(ctx)
        if left_val is not False and left_val is not None:
            return left_val
        return self.right.eval(ctx)


@dataclass
class UnaryOp(Expr):
    """
    Uma operação prefixa com um operando.

    Ex.: -x, !x
    """
    expr: Expr
    op: Callable
    
    def eval(self, ctx: Ctx):
        value = self.expr.eval(ctx)
        return self.op(value)


@dataclass
class Call(Expr):
    """
    Uma chamada de função.

    Ex.: fat(42)
    """
    func: Expr
    params: list[Expr]
    
    def eval(self, ctx: Ctx):
        func_obj = self.func.eval(ctx)
        params = []
        for param in self.params:
            params.append(param.eval(ctx))
        
        if callable(func_obj):
            return func_obj(*params)
        raise TypeError(f"Objeto não é uma função!")


@dataclass
class This(Expr):
    """
    Acesso ao `this`.

    Ex.: this
    """
    
    _placeholder: str = "this"
    
    def eval(self, ctx: Ctx):
        try:
            return ctx["this"]
        except KeyError:
            raise NameError("variável this não existe!")
    
    def validate_self(self, cursor):
        """
        Valida que this só pode aparecer dentro de uma classe.
        """
        from .node import Cursor
        from .errors import SemanticError
        
        for parent_cursor in cursor.parents():
            if isinstance(parent_cursor.node, Class):
                return  
        raise SemanticError("Can't use 'this' outside of a class.", token="this")


@dataclass
class Super(Expr):
    """
    Acesso a method ou atributo da superclasse.

    Ex.: super.method
    """
    
    method_name: str = ""
    
    def eval(self, ctx: Ctx):
        try:
            superclass = ctx["super"]
            this = ctx["this"]
            method = superclass.get_method(self.method_name)
            return method.bind(this)
        except KeyError as e:
            if "super" in str(e):
                raise NameError("variável super não existe!")
            elif "this" in str(e):
                raise NameError("variável this não existe!")
            else:
                raise
    
    def validate_self(self, cursor):
        """
        Valida que super só pode aparecer dentro de uma classe que herda de outra.
        """
        from .node import Cursor
        from .errors import SemanticError
        
        enclosing_class = None
        for parent_cursor in cursor.parents():
            if isinstance(parent_cursor.node, Class):
                enclosing_class = parent_cursor.node
                break
        
        if enclosing_class is None:
            raise SemanticError("Can't use 'super' outside of a class.", token="super")
        
        if enclosing_class.superclass is None:
            raise SemanticError("Can't use 'super' in a class with no superclass.", token="super")


@dataclass
class Assign(Expr):
    """
    Atribuição de variável.

    Ex.: x = 42
    """
    name: str
    value: Expr
    
    def eval(self, ctx: Ctx):
        result = self.value.eval(ctx)
        ctx.assign(self.name, result)
        return result


@dataclass
class Getattr(Expr):
    """
    Acesso a atributo de um objeto.

    Ex.: x.y
    """
    value: Expr
    attr: str

    def eval(self, ctx):
        from .runtime import LoxInstance, LoxClass
        obj = self.value.eval(ctx)
        
        if isinstance(obj, LoxInstance):
            return getattr(obj, self.attr)
        
        return getattr(obj, self.attr)


@dataclass
class Setattr(Expr):
    """
    Atribuição de atributo de um objeto.

    Ex.: x.y = 42
    """
    value: Expr
    attr: str
    expr: Expr

    def eval(self, ctx):
        from .runtime import LoxInstance, LoxClass, LoxFunction
        obj = self.value.eval(ctx)
        val = self.expr.eval(ctx)
        
        if isinstance(obj, (LoxClass, LoxFunction)):
            raise RuntimeError("Only instances have fields.")
        
        setattr(obj, self.attr, val)
        return val

@dataclass
class Print(Stmt):
    """
    Representa uma instrução de impressão.

    Ex.: print "Hello, world!";
    """
    expr: Expr
    
    def eval(self, ctx: Ctx):
        from .runtime import print
        value = self.expr.eval(ctx)
        print(value)


@dataclass
class Return(Stmt):
    """
    Representa um comando return.

    Ex.: return 42;
    """
    value: Expr | None = None
    
    def eval(self, ctx: Ctx):
        if self.value is not None:
            result = self.value.eval(ctx)
        else:
            result = None
        from .runtime import LoxReturn
        raise LoxReturn(result)
    
    def validate_self(self, cursor):
        """
        Valida que return só pode aparecer dentro de uma função.
        Também valida que return com valor não pode aparecer em init.
        """
        from .node import Cursor
        from .errors import SemanticError
        
        enclosing_function = None
        for parent_cursor in cursor.parents():
            if isinstance(parent_cursor.node, Function):
                enclosing_function = parent_cursor.node
                break
        
        if enclosing_function is None:
            raise SemanticError("Can't return from top-level code.", token="return")
            
        if enclosing_function.name == "init" and self.value is not None:
            function_parent = None
            for parent_cursor in cursor.parents():
                if isinstance(parent_cursor.node, Function) and parent_cursor.node == enclosing_function:
                    function_parent = parent_cursor.parent()
                    break
            if function_parent and isinstance(function_parent.node, Class):
                raise SemanticError("Can't return a value from an initializer.", token="return")


@dataclass
class VarDef(Stmt):
    """
    Representa uma declaração de variável.

    Ex.: var x = 42;
    """
    name: str
    value: Expr
    
    def eval(self, ctx: Ctx):
        result = self.value.eval(ctx)
        ctx.var_def(self.name, result)
        return ctx
    
    def validate_self(self, cursor: Cursor):
        reserved_words = {"true", "false", "nil", "return", "var", "fun", "class", "if", "else", "while", "for", "print", "and", "or", "this", "super"}
        
        if self.name in reserved_words:
            raise SemanticError("Expect variable name.", token=self.name)


@dataclass
class If(Stmt):
    """
    Representa uma instrução condicional.

    Ex.: if (x > 0) { ... } else { ... }
    """
    condition: Expr
    then_stmt: Stmt
    else_stmt: Stmt | None = None
    
    def eval(self, ctx: Ctx):
        from .runtime import truthy
        condition_val = self.condition.eval(ctx)
        
        if truthy(condition_val):
            self.then_stmt.eval(ctx)
        elif self.else_stmt is not None:
            self.else_stmt.eval(ctx)


@dataclass
class While(Stmt):
    """
    Representa um laço de repetição.

    Ex.: while (x > 0) { ... }
    """
    condition: Expr
    body: Stmt
    
    def eval(self, ctx: Ctx):
        from .runtime import truthy
        while True:
            condition_val = self.condition.eval(ctx)
            if not truthy(condition_val):
                break
            self.body.eval(ctx)


@dataclass
class Block(Stmt):
    """
    Representa bloco de comandos.

    Ex.: { var x = 42; print x;  }
    """
    stmts: list[Stmt]
    
    def eval(self, ctx: Ctx):
        new_ctx = ctx.push({})
        for stmt in self.stmts:
            stmt.eval(new_ctx)
    
    def validate_self(self, cursor: Cursor):
        declared_vars = set()
        
        for stmt in self.stmts:
            if isinstance(stmt, VarDef):
                if stmt.name in declared_vars:
                    raise SemanticError("Already a variable with this name in this scope.", token=stmt.name)
                declared_vars.add(stmt.name)
        parent = cursor.parent_cursor
        while parent:
            if isinstance(parent.node, Function):
                for stmt in self.stmts:
                    if isinstance(stmt, VarDef):
                        if stmt.name in parent.node.params:
                            raise SemanticError("Already a variable with this name in this scope.", token=stmt.name)
                break
            parent = parent.parent_cursor


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
        from .runtime import LoxFunction
        function = LoxFunction(self.name, self.params, self.body, ctx)
        ctx.var_def(self.name, function)
        return function
    
    def validate_self(self, cursor: Cursor):
        reserved_words = {"true", "false", "nil", "return", "var", "fun", "class", "if", "else", "while", "for", "print", "and", "or", "this", "super"}
        
        for param in self.params:
            param_name = param.name if hasattr(param, 'name') else param
            if param_name in reserved_words:
                raise SemanticError("Expect variable name.", token=param_name)
        
        param_names = [param.name if hasattr(param, 'name') else param for param in self.params]
        param_set = set(param_names)
        
        if len(param_set) != len(param_names):
            seen = set()
            for param in self.params:
                param_name = param.name if hasattr(param, 'name') else param
                if param_name in seen:
                    raise SemanticError("Already a variable with this name in this scope.", token=param_name)
                seen.add(param_name)


@dataclass
class Class(Stmt):
    """
    Representa uma classe.

    Ex.: class B < A { ... }
    """
    name: str
    methods: list["Function"]
    superclass: str = None
    
    def eval(self, ctx: Ctx):
        from .runtime import LoxClass, LoxFunction

        superclass = None
        if self.superclass is not None:
            superclass = ctx[self.superclass]
            if not isinstance(superclass, LoxClass):
                raise SemanticError(f"Superclass must be a class.")
                
        class_name = self.name
        method_defs = self.methods
    
        if superclass is None:
            method_ctx = ctx
        else:
            method_ctx = ctx.push({"super": superclass})
            
        methods = {}
        for method in method_defs:
            method_name = method.name
            method_body = method.body
            method_args = method.params
            method_impl = LoxFunction(method_name, method_args, method_body, method_ctx)
            methods[method_name] = method_impl

        lox_class = LoxClass(class_name, methods, superclass)
        ctx.var_def(self.name, lox_class)
        return lox_class
    
    def validate_self(self, cursor):
        """
        Valida que uma classe não pode herdar de si mesma.
        """
        from .errors import SemanticError
        
        if self.superclass is not None and self.superclass == self.name:
            raise SemanticError("A class can't inherit from itself.", token=self.superclass)

from .runtime import LoxClass, LoxError, LoxInstance