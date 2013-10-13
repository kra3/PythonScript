#!/usr/bin/env python
import os, sys, pickle
from types import GeneratorType

from ast import Str
from ast import Call
from ast import Name
from ast import Tuple
from ast import Assign
from ast import keyword
from ast import Subscript
from ast import Attribute
from ast import FunctionDef
from ast import BinOp
from ast import Pass
from ast import Global

from ast import parse
from ast import NodeVisitor

if sys.version_info.major == 3:
    import io
    StringIO = io.StringIO
else:
    from cStringIO import StringIO as StringIO


try:
    _log_file = open('/tmp/python_to_pythonjs.log', 'wb')
except:
    _log_file = None
def log(txt):
    if _log_file:
        _log_file.write( str(txt)+'\n' )
        _log_file.flush()


GLOBAL_VARIABLE_SCOPE = False              ## Python style
if '--global-variable-scope' in sys.argv:  ## JavaScript style
    GLOBAL_VARIABLE_SCOPE = True
    log('not using python style variable scope')

class Writer(object):

    def __init__(self):
        self.level = 0
        self.buffers = list()
        self.output = StringIO()
        self.with_javascript = False

    def push(self):
        self.level += 1

    def pull(self):
        self.level -= 1

    def append(self, code):
        self.buffers.append(code)

    def write(self, code):
        for buffer in self.buffers:
            self._write(buffer)
        self.buffers = list()
        self._write(code)

    def _write(self, code):
        indentation = self.level * 4 * ' '
        if self.with_javascript: code = """JS('''%s''')"""%code
        self.output.write('%s%s\n' % (indentation, code))

    def getvalue(self):
        s = self.output.getvalue()
        self.output = StringIO()
        return s

writer = Writer()

MINI_STDLIB = {
    'time': {
        'time': 'function time() { return new Date().getTime() / 1000.0; }'
    },
    'random': {
        'random': 'var random = Math.random'
    }
}

class Typedef(object):
    # http://docs.python.org/2/reference/datamodel.html#emulating-numeric-types
    _opmap = dict(
        __add__ = '+',
        __iadd__ = '+=',
        __sub__ = '-',
        __isub__ = '-=',
        __mul__ = '*',
        __imul__ = '*=',
        __div__ = '/',
        __idiv__ = '/=',
        __mod__ = '%',
        __imod__ = '%=',
        __lshift__ = '<<',
        __ilshift__ = '<<=',
        __rshift__ = '>>',
        __irshift__ = '>>=',
        __and__ = '&',
        __iand__ = '&=',
        __xor__ = '^',
        __ixor__ = '^=',
        __or__ = '|',
        __ior__ = '|=',
    )

    def __init__(self, **kwargs):
        for name in kwargs.keys():
            setattr( self, name, kwargs[name] )

        self.operators = dict()
        for name in self.methods:
            if name in self._opmap:
                op = self._opmap[ name ]
                self.operators[ op ] = self.get_pythonjs_function_name( name )

    def get_pythonjs_function_name(self, name):
        assert name in self.methods
        return '__%s_%s' %(self.name, name) ## class name

    def check_for_parent_with(self, method=None, property=None, operator=None, class_attribute=None):
        log('check_for_parent_with: %s'%locals())
        log('self.parents: %s'%self.parents)

        for parent_name in self.parents:
            typedef = self.compiler.get_typedef( class_name=parent_name )
            if method and method in typedef.methods:
                return typedef
            elif property and property in typedef.properties:
                return typedef
            elif operator and typedef.operators:
                return typedef
            elif class_attribute in typedef.class_attributes:
                return typedef
            elif typedef.parents:
                res = typedef.check_for_parent_with(
                    method=method, 
                    property=property, 
                    operator=operator,
                    class_attribute=class_attribute
                )
                if res:
                    return res

class PythonToPythonJS(NodeVisitor):

    identifier = 0

    def __init__(self, module=None, module_path=None):
        super(PythonToPythonJS, self).__init__()
        self._classes = dict()    ## class name : [method names]
        self._class_parents = dict()  ## class name : parents
        self._instance_attributes = dict()  ## class name : [attribute names]
        self._class_attributes = dict()
        self._catch_attributes = None
        self._names = set() ## not used?
        self._instances = dict()  ## instance name : class name
        self._decorator_properties = dict()
        self._decorator_class_props = dict()
        self._function_return_types = dict()
        self._return_type = None
        self._module = module
        self._module_path = module_path
        self._with_js = False
        self._typedefs = dict()  ## class name : typedef  (not pickled)
        self.setup_builtins()

    def setup_builtins(self):
        self._classes['dict'] = set(['__getitem__', '__setitem__'])
        self._classes['list'] = set(['__getitem__', '__setitem__'])
        self._classes['tuple'] = set(['__getitem__', '__setitem__'])
        self._builtins = set(['dict', 'list', 'tuple'])

    def get_typedef(self, instance=None, class_name=None):
        assert instance or class_name
        if isinstance(instance, Name) and instance.id in self._instances:
            class_name = self._instances[ instance.id ]

        if class_name:
            #assert class_name in self._classes
            if class_name not in self._classes:
                log('ERROR: class name not in self._classes: %s'%class_name)
                log('self._classes: %s'%self._classes)
                raise RuntimeError('class name: %s - not found in self._classes - node:%s '%(class_name, instance))

            if class_name not in self._typedefs:
                self._typedefs[ class_name ] = Typedef(
                    name = class_name,
                    methods = self._classes[ class_name ],
                    #properties = self._decorator_class_props[ class_name ],
                    #attributes = self._instance_attributes[ class_name ],
                    #class_attributes = self._class_attributes[ class_name ],
                    #parents = self._class_parents[ class_name ],
                    properties = self._decorator_class_props.get(  class_name, set()),
                    attributes = self._instance_attributes.get(    class_name, set()),
                    class_attributes = self._class_attributes.get( class_name, set()),
                    parents = self._class_parents.get(             class_name, set()),

                    compiler = self,
                )
            return self._typedefs[ class_name ]

    def save_module(self):
        if self._module and self._module_path:
            a = dict(
                classes = self._classes,
                instance_attributes = self._instance_attributes,
                class_attributes = self._class_attributes,
                decorator_class_props = self._decorator_class_props,
                function_return_types = self._function_return_types,
                class_parents = self._class_parents,
            )
            pickle.dump( a, open(os.path.join(self._module_path, self._module+'.module'), 'wb') )

    def visit_ImportFrom(self, node):
        if node.module in MINI_STDLIB:
            for n in node.names:
                if n.name in MINI_STDLIB[ node.module ]:
                    writer.write( 'JS("%s")' %MINI_STDLIB[node.module][n.name] )

        elif self._module_path and node.module+'.module' in os.listdir(self._module_path):
            f = open( os.path.join(self._module_path, node.module+'.module'), 'rb' )
            a = pickle.load( f ); f.close()
            self._classes.update( a['classes'] )
            self._class_attributes.update( a['class_attributes'] )
            self._instance_attributes.update( a['instance_attributes'] )
            self._decorator_class_props.update( a['decorator_class_props'] )
            self._function_return_types.update( a['function_return_types'] )
            self._class_parents.update( a['class_parents'] )

    def visit_Assert(self, node):
        ## hijacking "assert isinstance(a,A)" as a type system ##
        if isinstance( node.test, Call ) and isinstance(node.test.func, Name) and node.test.func.id == 'isinstance':
            a,b = node.test.args
            if b.id in self._classes:
                self._instances[ a.id ] = b.id

    def visit_Dict(self, node):
        node.returns_type = 'dict'
        #keys = [x.s for x in node.keys]
        #values = map(self.visit, node.values)
        #a = [ '%s=%s'%x for x in zip(keys, values) ]
        #b = 'JSObject(%s)' %', '.join(a)
        #return 'get_attribute(dict, "__call__")([], JSObject(js_object=%s))' %b
        a = []
        for i in range( len(node.keys) ):
            k = self.visit( node.keys[ i ] )
            v = self.visit( node.values[i] )
            if self._with_js:
                a.append( '%s:%s'%(k,v) )
            else:
                a.append( 'JSObject(key=%s, value=%s)'%(k,v) )
        if self._with_js:
            b = ','.join( a )
            return '{ %s }' %b
        else:
            b = '[%s]' %', '.join(a)
            return 'get_attribute(dict, "__call__")([], JSObject(js_object=%s))' %b

    def visit_Tuple(self, node):
        a = '[%s]' % ', '.join(map(self.visit, node.elts))
        return 'get_attribute(tuple, "__call__")([], JSObject(js_object=%s))' %a

    def visit_List(self, node):
        a = '[%s]' % ', '.join(map(self.visit, node.elts))
        if self._with_js:
            return a
        else:
            return 'get_attribute(list, "__call__")([], JSObject(js_object=%s))' %a

    def visit_In(self, node):
        return ' in '

    def visit_AugAssign(self, node):
        target = self.visit( node.target )
        op = '%s=' %self.visit( node.op )

        typedef = self.get_typedef( node.target )
        if typedef and op in typedef.operators:
            func = typedef.operators[ op ]
            a = '%s( [%s, %s] )' %(func, target, self.visit(node.value))
            writer.write( a )
        else:
            ## TODO extra checks to make sure the operator type is valid in this context
            a = '%s %s %s' %(target, op, self.visit(node.value))
            writer.write(a)

    def visit_Yield(self, node):
        return 'yield %s' % self.visit(node.value)


    def visit_ClassDef(self, node):
        name = node.name
        log('ClassDef: %s'%name)
        self._classes[ name ] = list()  ## method names
        self._class_parents[ name ] = set()
        self._class_attributes[ name ] = set()
        self._catch_attributes = None
        self._decorator_properties = dict() ## property names :  {'get':func, 'set':func}
        self._decorator_class_props[ name ] = self._decorator_properties
        self._instances[ 'self' ] = name

        #for dec in node.decorator_list:  ## TODO class decorators
        #    if isinstance(dec, Name) and dec.id == 'inline':  ## @inline class decorator is DEPRECATED
        #        self._catch_attributes = set()
        ## always catch attributes ##
        self._catch_attributes = set()
        self._instance_attributes[ name ] = self._catch_attributes


        writer.write('var(%s, __%s_attrs, __%s_parents)' % (name, name, name))
        writer.write('window["__%s_attrs"] = JSObject()' % name)
        writer.write('window["__%s_parents"] = JSArray()' % name)
        for base in node.bases:
            code = '__%s_parents.push(%s)' % (name, self.visit(base))
            writer.write(code)
            if isinstance(base, Name):
                self._class_parents[ name ].add( base.id )
            else:
                raise NotImplementedError

        for item in node.body:
            if isinstance(item, FunctionDef):
                log('  method: %s'%item.name)
                self._classes[ name ].append( item.name )
                item_name = item.name
                item.original_name = item.name
                item.name = '__%s_%s' % (name, item_name)

                self.visit(item)  # this will output the code for the function

                if item_name in self._decorator_properties:
                    pass
                else:
                    writer.write('window["__%s_attrs"]["%s"] = %s' % (name, item_name, item.name))

            elif isinstance(item, Assign) and isinstance(item.targets[0], Name):
                item_name = item.targets[0].id
                item.targets[0].id = '__%s_%s' % (name, item_name)
                self.visit(item)  # this will output the code for the assign
                writer.write('window["__%s_attrs"]["%s"] = %s' % (name, item_name, item.targets[0].id))
                self._class_attributes[ name ].add( item_name )  ## should this come before self.visit(item) ??
            elif isinstance(item, Pass):
                pass
            else:
                raise NotImplementedError

        self._catch_attributes = None
        self._decorator_properties = None
        self._instances.pop('self')

        writer.write('%s = create_class("%s", window["__%s_parents"], window["__%s_attrs"])' % (name, name, name, name))

    def visit_If(self, node):
        writer.write('if %s:' % self.visit(node.test))
        writer.push()
        map(self.visit, node.body)
        writer.pull()
        if node.orelse:
            writer.write('else:')
            writer.push()
            map(self.visit, node.orelse)
            writer.pull()

    def visit_TryExcept(self, node):
        writer.write('try:')
        writer.push()
        map(self.visit, node.body)
        writer.pull()
        map(self.visit, node.handlers)

    def visit_Raise(self, node):
        writer.write('raise %s' % self.visit(node.type))

    def visit_ExceptHandler(self, node):
        if node.type and node.name:
            writer.write('except %s, %s:' % (self.visit(node.type), self.visit(node.name)))
        elif node.type and not node.name:
            writer.write('except %s:' % self.visit(node.type))
        else:
            writer.write('except:')
        writer.push()
        map(self.visit, node.body)
        writer.pull()

    def visit_Pass(self, node):
        writer.write('pass')

    def visit_Name(self, node):
        return node.id

    def visit_Num(self, node):
        return str(node.n)

    def visit_Return(self, node):
        if node.value:
            if isinstance(node.value, Call) and isinstance(node.value.func, Name) and node.value.func.id in self._classes:
                self._return_type = node.value.func.id
            elif isinstance(node.value, Name) and node.value.id == 'self' and 'self' in self._instances:
                self._return_type = self._instances['self']

            writer.write('return %s' % self.visit(node.value))

        else:
            raise RuntimeError

    def visit_BinOp(self, node):
        left = self.visit(node.left)
        op = self.visit(node.op)
        right = self.visit(node.right)
        #if isinstance(node.left, Name) and node.left.id in self._instances:
        #    klass = self._instances[ node.left.id ]
        #    if op == '*' and '__mul__' in self._classes[klass]:
        #        node.operator_overloading = '__%s___mul__' %klass
        #        assert node.operator_overloading
        #        return '''JS('__%s___mul__( [%s, %s] )')''' %(klass, left, right)
        if isinstance(node.left, Name):
            typedef = self.get_typedef( node.left )
            if typedef and op in typedef.operators:
                func = typedef.operators[ op ]
                node.operator_overloading = func
                return '''JS('%s( [%s, %s] )')''' %(func, left, right)

        return '%s %s %s' % (left, op, right)

    def visit_Eq(self, node):
        return '=='

    def visit_NotEq(self, node):
        return '!='

    def visit_Is(self, node):
        return 'is'

    def visit_Mult(self, node):
        return '*'

    def visit_Add(self, node):
        return '+'

    def visit_Sub(self, node):
        return '-'

    def visit_Div(self, node):
        return '/'
    def visit_Mod(self, node):
        return '%'
    def visit_LShift(self, node):
        return '<<'
    def visit_RShift(self, node):
        return '>>'
    def visit_BitXor(self, node):
        return '^'
    def visit_BitOr(self, node):
        return '|'
    def visit_BitAnd(self, node):
        return '&'

    def visit_Lt(self, node):
        return '<'

    def visit_Gt(self, node):
        return '>'

    def visit_GtE(self, node):
        return '>='

    def visit_LtE(self, node):
        return '<='

    def visit_Compare(self, node):
        left = self.visit(node.left)
        ops = self.visit(node.ops[0])
        comparator = self.visit(node.comparators[0])
        return '%s %s %s' % (left, ops, comparator)

    def visit_Not(self, node):
        return ' not '

    def visit_UnaryOp(self, node):
        return self.visit(node.op) + self.visit(node.operand)

    def visit_Attribute(self, node):
        node_value = self.visit(node.value)

        if self._with_js:
            return '%s.%s' %(node_value, node.attr)
        typedef = None
        if isinstance(node.value, Name):
            typedef = self.get_typedef( instance=node.value )
        elif hasattr(node.value, 'returns_type'):
            typedef = self.get_typedef( class_name=node.value.returns_type )

        if typedef:
            if node.attr in typedef.properties:
                getter = typedef.properties[ node.attr ]['get']
                if getter in self._function_return_types:
                    node.returns_type = self._function_return_types[getter]
                return '%s( [%s] )' %(getter, node_value)
            elif node.attr in typedef.class_attributes:
                return "%s['__class__']['__dict__']['%s']" %(node_value, node.attr)
            elif node.attr in typedef.attributes:
                return "%s['__dict__']['%s']" %(node_value, node.attr)
            elif '__getattr__' in typedef.methods:
                func = typedef.get_pythonjs_function_name( '__getattr__' )
                return '%s([%s, "%s"])' %(func, node_value, node.attr)

            elif typedef.check_for_parent_with( property=node.attr ):
                parent = typedef.check_for_parent_with( property=node.attr )
                getter = parent.properties[ node.attr ]['get']
                if getter in self._function_return_types:
                    node.returns_type = self._function_return_types[getter]
                return '%s( [%s] )' %(getter, node_value)
            elif typedef.check_for_parent_with( class_attribute=node.attr ):
                #return 'get_attribute(%s, "%s")' % (node_value, node.attr)  ## get_attribute is broken with grandparent class attributes
                parent = typedef.check_for_parent_with( class_attribute=node.attr )
                return "window['__%s_attrs']['%s']" %(parent.name, node.attr)
            elif typedef.check_for_parent_with( method='__getattr__' ):
                parent = typedef.check_for_parent_with( method='__getattr__' )
                func = parent.get_pythonjs_function_name( '__getattr__' )
                return '%s([%s, "%s"])' %(func, node_value, node.attr)

            else:
                return 'get_attribute(%s, "%s")' % (node_value, node.attr)
        else:
            return 'get_attribute(%s, "%s")' % (node_value, node.attr)


    def visit_Index(self, node):
        return self.visit(node.value)

    def visit_Subscript(self, node):
        name = self.visit(node.value)

        if self._with_js:
            return '%s[ %s ]' %(name, self.visit(node.slice))

        if name in self._instances:  ## support x[y] operator overloading
            klass = self._instances[ name ]
            if '__getitem__' in self._classes[ klass ]:
                return '__%s___getitem__( [%s, %s] )' % (klass, name, self.visit(node.slice))
            else:
                return 'get_attribute(%s, "__getitem__")([%s], JSObject())' % (
                    self.visit(node.value),
                    self.visit(node.slice),
                )
        else:
            return 'get_attribute(%s, "__getitem__")([%s], JSObject())' % (
                self.visit(node.value),
                self.visit(node.slice),
            )

    def visit_Slice(self, node):
        return "get_attribute(Slice, '__call__')([%s, %s, %s], JSObject())" % (self.visit(node.lower), self.visit(node.upper), self.visit(node.step))

    def visit_Assign(self, node):
        # XXX: support only one target for subscripts
        target = node.targets[0]
        if isinstance(target, Subscript):
            if self._with_js:
                code = '%s[ %s ] = %s'
            else:
                code = "get_attribute(get_attribute(%s, '__setitem__'), '__call__')([%s, %s], JSObject())"
            code = code % (self.visit(target.value), self.visit(target.slice.value), self.visit(node.value))
            writer.write(code)

        elif isinstance(target, Attribute):
            target_value = self.visit(target.value)  ## target.value may have "returns_type" after being visited
            typedef = None
            if isinstance(target.value, Name):
                if target.value.id == 'self' and isinstance(self._catch_attributes, set):
                    self._catch_attributes.add( target.attr )
                typedef = self.get_typedef( instance=target.value )
            elif hasattr(target.value, 'returns_type'):
                typedef = self.get_typedef( class_name=target.value.returns_type )


            if typedef and target.attr in typedef.properties and 'set' in typedef.properties[ target.attr ]:
                setter = typedef.properties[ target.attr ]['set']
                writer.write( '%s( [%s, %s] )' %(setter, target_value, self.visit(node.value)) )
            elif typedef and target.attr in typedef.class_attributes:
                writer.write( '''%s['__class__']['__dict__']['%s'] = %s''' %(target_value, target.attr, self.visit(node.value)))
            elif typedef and target.attr in typedef.attributes:
                writer.write( '''%s['__dict__']['%s'] = %s''' %(target_value, target.attr, self.visit(node.value)))

            elif typedef and typedef.parents:
                parent_prop = typedef.check_for_parent_with( property=target.attr )
                parent_classattr = typedef.check_for_parent_with( class_attribute=target.attr )
                parent_setattr = typedef.check_for_parent_with( method='__setattr__' )
                if parent_prop and 'set' in parent_prop.properties[target.attr]:
                    setter = parent_prop.properties[target.attr]['set']
                    writer.write( '%s( [%s, %s] )' %(setter, target_value, self.visit(node.value)) )
                elif parent_classattr:
                    writer.write( "window['__%s_attrs']['%s'] = %s" %(parent_classattr.name, target.attr, self.visit(node.value)) )
                elif parent_setattr:
                    func = parent_setattr.get_pythonjs_function_name( '__setattr__' )
                    writer.write( '%s([%s, "%s", %s])' %(func, target_value, target.attr, self.visit(node.value)) )

                elif '__setattr__' in typedef.methods:
                    func = typedef.get_pythonjs_function_name( '__setattr__' )
                    writer.write( '%s([%s, "%s", %s])' %(func, target_value, target.attr, self.visit(node.value)) )

                else:
                    code = 'set_attribute(%s, "%s", %s)' % (
                        target_value,
                        target.attr,
                        self.visit(node.value)
                    )
                    writer.write(code)

            elif typedef and '__setattr__' in typedef.methods:
                func = typedef.get_pythonjs_function_name( '__setattr__' )
                log('__setattr__ in instance typedef.methods - func:%s target_value:%s target_attr:%s' %(func, target_value, target_attr))
                writer.write( '%s([%s, "%s", %s])' %(func, target_value, target.attr, self.visit(node.value)) )


            else:
                code = 'set_attribute(%s, "%s", %s)' % (
                    target_value,
                    target.attr,
                    self.visit(node.value)
                )
                writer.write(code)

        elif isinstance(target, Name):
            node_value = self.visit( node.value )  ## node.value may have extra attributes after being visited

            if isinstance(node.value, Call) and hasattr(node.value.func, 'id') and node.value.func.id in self._classes:
                self._instances[ target.id ] = node.value.func.id  ## keep track of instances
            elif isinstance(node.value, Call) and isinstance(node.value.func, Name) and node.value.func.id in self._function_return_types:
                self._instances[ target.id ] = self._function_return_types[ node.value.func.id ]
            elif isinstance(node.value, Call) and isinstance(node.value.func, Attribute) and isinstance(node.value.func.value, Name) and node.value.func.value.id in self._instances:
                typedef = self.get_typedef( node.value.func.value )
                method = node.value.func.attr
                if method in typedef.methods:
                    func = typedef.get_pythonjs_function_name( method )
                    if func in self._function_return_types:
                        self._instances[ target.id ] = self._function_return_types[ func ]
                    else:
                        writer.write('## %s - unknown return type for: %s' % (typedef.name, func))
                else:
                    writer.write('## %s - not a method: %s' %(typedef.name, method))

            elif isinstance(node.value, Name) and node_value in self._instances:  ## if this is a simple copy: "a = b" and "b" is known to be of some class
                self._instances[ target.id ] = self._instances[ node_value ]
            elif isinstance(node.value, BinOp) and hasattr(node.value, 'operator_overloading') and node.value.operator_overloading in self._function_return_types:
                self._instances[ target.id ] = self._function_return_types[ node.value.operator_overloading ]
            elif hasattr(node.value, 'returns_type'):
                self._instances[ target.id ] = node.value.returns_type
            elif target.id in self._instances:
                self._instances.pop( target.id )

            writer.write('%s = %s' % (target.id, node_value))

        else:  # it's a Tuple
            id = self.identifier
            self.identifier += 1
            r = '__r_%s' % id
            writer.write('var(%s)' % r)
            writer.write('%s = %s' % (r, self.visit(node.value)))
            for i, target in enumerate(target.elts):
                if isinstance(target, Attribute):
                    code = 'set_attribute(%s, "%s", %s[%s])' % (
                        self.visit(target.value),
                        target.attr,
                        r,
                        i
                    )
                    writer.write(code)
                else:
                    writer.write('%s = %s[%s]' % (target.id, r, i))

    def visit_Print(self, node):
        writer.write('print %s' % ', '.join(map(self.visit, node.values)))

    def visit_Str(self, node):
        if self._with_js:
            return '"%s"' %node.s
        else:
            return '"""%s"""' % node.s

    def visit_Expr(self, node):
        writer.write(self.visit(node.value))

    def visit_Call(self, node):
        if self._with_js:
            args = list( map(self.visit, node.args) )
            a = ','.join(args)
            return '%s( %s )' %( self.visit(node.func), a )

        if hasattr(node.func, 'id') and node.func.id in ('JS', 'toString', 'JSObject', 'JSArray', 'var'):
            args = list( map(self.visit, node.args) ) ## map in py3 returns an iterator not a list
            if node.func.id == 'var':
                for k in node.keywords:
                    self._instances[ k.arg ] = k.value.id
                    args.append( k.arg )
            else:
                kwargs = map(lambda x: '%s=%s' % (x.arg, self.visit(x.value)), node.keywords)
                args.extend(kwargs)
            args = ', '.join(args)
            return '%s(%s)' % (node.func.id, args)
        else:

            call_has_args = len(node.args) or len(node.keywords) or node.starargs or node.kwargs
            name = self.visit(node.func)

            if call_has_args:
                args = ', '.join(map(self.visit, node.args))
                kwargs = ', '.join(map(lambda x: '%s=%s' % (x.arg, self.visit(x.value)), node.keywords))
                args_name = '__args_%s' % self.identifier
                kwargs_name = '__kwargs_%s' % self.identifier

                writer.append('var(%s, %s)' % (args_name, kwargs_name))
                self.identifier += 1

                if name in ('list', 'tuple'):
                    writer.write( '%s = JS("%s.__dict__.js_object")' % (args_name, args))
                else:
                    writer.append('%s = JSArray(%s)' % (args_name, args))

                if node.starargs:
                    writer.append('%s.push.apply(%s, %s)' % (args_name, args_name, self.visit(node.starargs)))
                writer.append('%s = JSObject(%s)' % (kwargs_name, kwargs))

                if node.kwargs:
                    kwargs = self.visit(node.kwargs)
                    code = "JS('for (var name in %s) { %s[name] = %s[name]; }')" % (kwargs, kwargs_name, kwargs)
                    writer.append(code)

            if call_has_args:
                if name == 'dict':
                    return 'get_attribute(%s, "__call__")(%s, JSObject(js_object=%s))' % (name, args_name, kwargs_name)
                elif name in ('list', 'tuple'):
                    return 'get_attribute(%s, "__call__")([], JSObject(js_object=%s))' % (name, args_name)
                else:
                    return 'get_attribute(%s, "__call__")(%s, %s)' % (name, args_name, kwargs_name)

            elif name in self._classes or name in self._builtins:
                return 'get_attribute(%s, "__call__")( JSArray(), JSObject() )' %name

            else:  ## this could be a dangerous optimization ##
                return '%s( JSArray(), JSObject() )' %name

    def visit_FunctionDef(self, node):
        property_decorator = None
        decorators = []
        for decorator in reversed(node.decorator_list):
            log('@decorator: %s' %decorator)

            if isinstance(decorator, Name) and decorator.id == 'property':
                property_decorator = decorator
                n = node.name + '__getprop__'
                self._decorator_properties[ node.original_name ] = dict( get=n, set=None )
                node.name = n

            elif isinstance(decorator, Attribute) and isinstance(decorator.value, Name) and decorator.value.id in self._decorator_properties:
                if decorator.attr == 'setter':
                    if self._decorator_properties[ decorator.value.id ]['set']:
                        raise SyntaxError('user error - the same decorator.setter is used more than once!')
                    n = node.name + '__setprop__'
                    self._decorator_properties[ decorator.value.id ]['set'] = n
                    node.name = n
                elif decorator.attr == 'deleter':
                    raise NotImplementedError
                else:
                    raise RuntimeError

            else:
                decorators.append( decorator )

        log('function: %s'%node.name)
        writer.write('def %s(args, kwargs):' % node.name)
        writer.push()

        ## the user will almost always want to use Python-style variable scope,
        ## this is kept here as an option to be sure we are compatible with the
        ## old-style code in runtime/pythonpythonjs.py and runtime/builtins.py
        if not GLOBAL_VARIABLE_SCOPE:
            local_vars = set()
            global_vars = set()
            for n in node.body:
                if isinstance(n, Assign) and isinstance(n.targets[0], Name):  ## assignment to local
                    local_vars.add( n.targets[0].id )
                elif isinstance(n, Global):
                    global_vars.update( n.names )
            if local_vars-global_vars:
                a = ','.join( local_vars-global_vars )
                writer.write('var(%s)' %a)

        if len(node.args.defaults) or len(node.args.args) or node.args.vararg or node.args.kwarg:
            # new pythonjs' python function arguments handling
            # create the structure representing the functions arguments
            # first create the defaultkwargs JSObject
            writer.write('var(signature, arguments)')
            L = len(node.args.defaults)
            kwargsdefault = map(lambda x: keyword(self.visit(x[0]), x[1]), zip(node.args.args[-L:], node.args.defaults))
            kwargsdefault = Call(
                Name('JSObject', None),
                [],
                kwargsdefault,
                None,
                None
            )
            args = Call(
                Name('JSArray', None),
                map(lambda x: Str(x.id), node.args.args),
                [],
                None,
                None
            )
            keywords = list([
                keyword(Name('kwargs', None), kwargsdefault),
                keyword(Name('args', None), args),
            ])
            if node.args.vararg:
                keywords.append(keyword(Name('vararg', None), Str(node.args.vararg)))
            if node.args.kwarg:
                keywords.append(keyword(Name('varkwarg', None), Str(node.args.kwarg)))

            # create a JS Object to store the value of each parameter
            signature = ', '.join(map(lambda x: '%s=%s' % (self.visit(x.arg), self.visit(x.value)), keywords))
            writer.write('signature = JSObject(%s)' % signature)
            writer.write('arguments = get_arguments(signature, args, kwargs)')
            # # then for each argument assign its value
            for arg in node.args.args:
                writer.write("""JS("var %s = arguments['%s']")""" % (arg.id, arg.id))
            if node.args.vararg:
                writer.write("""JS("var %s = arguments['%s']")""" % (node.args.vararg, node.args.vararg))
                # turn it into a list
                expr = '%s = get_attribute(list, "__call__")(create_array(%s), {});'
                expr = expr % (node.args.vararg, node.args.vararg)
                writer.write(expr)
            if node.args.kwarg:
                writer.write("""JS('var %s = arguments["%s"]')""" % (node.args.kwarg, node.args.kwarg))
                expr = '%s = get_attribute(dict, "__call__")(create_array(%s), {});'
                expr = expr % (node.args.kwarg, node.args.kwarg)
                writer.write(expr)
        else:
            log('(function has no arguments)')

        self._return_type = None
        map(self.visit, node.body)

        if self._return_type:
            self._function_return_types[ node.name ] = self._return_type

        writer.pull()
        writer.write('%s.pythonscript_function=True'%node.name)
        # apply decorators
        for decorator in decorators:
            writer.write('%s = %s(create_array(%s))' % (node.name, self.visit(decorator), node.name))

    def visit_For(self, node):
        writer.write('var(__iterator__, %s)' % node.target.id)
        writer.write('__iterator__ = get_attribute(get_attribute(%s, "__iter__"), "__call__")(JSArray(), JSObject())' % self.visit(node.iter))
        writer.write('try:')
        writer.push()
        writer.write('%s = get_attribute(__iterator__, "next")(JSArray(), JSObject())' % node.target.id)
        writer.write('while True:')
        writer.push()
        map(self.visit, node.body)
        writer.write('%s = get_attribute(__iterator__, "next")(JSArray(), JSObject())' % node.target.id)
        writer.pull()
        writer.pull()
        writer.write('except StopIteration:')
        writer.push()
        writer.write('pass')
        writer.pull()
        return ''

    def visit_While(self, node):
        writer.write('while %s:' % self.visit(node.test))
        writer.push()
        map(self.visit, node.body)
        writer.pull()

    def visit_With(self, node):
        if isinstance( node.context_expr, Name ) and node.context_expr.id == 'javascript':
            self._with_js = True
            writer.with_javascript = True
            map(self.visit, node.body)
            writer.with_javascript = False
            self._with_js = False


def main(script):
    input = parse(script)
    PythonToPythonJS().visit(input)
    return writer.getvalue()


def command():
    module = module_path = None

    data = sys.stdin.read()
    if data.startswith('#!'):
        header = data[ 2 : data.index('\n') ]
        data = data[ data.index('\n')+1 : ]
        if ';' in header:
            module_path, module = header.split(';')
        else:
            module_path = header

    compiler = PythonToPythonJS( module=module, module_path=module_path )
    compiler.visit( parse(data) )
    compiler.save_module()
    output = writer.getvalue()
    print( output )  ## pipe to stdout


if __name__ == '__main__':
    command()
