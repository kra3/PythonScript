Changelog
#########

0.8
===

Tools
~~~~~

- Tornado compiler server can be found in ``tests/server.py``
- Tests

New
~~~

- added support for subscript ``[]`` operator
- added simple generators via ``yield``
- added support of inplace assignements
- added support for operator overloading
- added support for get ``__getattr__`` and set ``__setattr__`` attribute overloading
- added support for subscript operator overloading ``__getitem__``
- added ``assert isinstance(some_instance, SomeClass)`` as a hackish type-system
- added partial support of ``in`` operator, it works only on javascript objects and fails for arrays.
- added support for list literals ``[1, 2, 3]``
- added a mini standard library with ``time``, ``random``
- added ``@inline`` decorator, to speed up attribute access
- optimized functions with no arguments
- optimized functions calls with no arguments
- added support for Google Closure Compiler
- added support for ``@property`` **gotcha:** you cannot use the same decorator setter more than once...
- added support for ``var(x=SomeType)`` which declares a variable ``x`` to be of type ``SomeType`` to optimize your code
- added support for mutiply operator ``*``
- added dynamic wrapping of any Javascript function
- added support for ``global`` and removes the need to use ``var()`` for non-typed variables
- added support for both init styles of dict ``{'x': 1}`` and ``dict(x=1)``
- added init of empty list
- added tuple type
- added support for keys of any type in dictionaries
- improvements to ``dict``
- added ``array`` class that wraps ``ArrayBuffer`` and ``DataView``
- added builtins ``ord``, ``chr``, ``min`` and ``abs``
- added support for ``with javascript:`` syntax that allows for simple insertion of python-javascript without having to use manually ``JS("..")``
- added three.js wrappers

Fixed bugs
~~~~~~~~~~

- fix a code containing using ``*args`` special argument lead to buggy code
- fixes in jQuery bindings

Internal
~~~~~~~~

- Cleanup
- Added logging facility
- Support of Python3


0.7.4 - Get the party started
=============================

- Fix again the ``pythonscript``

0.7.3 - Tricky
==============

- Fixed ``pythnonjs`` and ``python_to_pythonjs`` commands to be runnable.

0.7.2 - Urban species
=====================

- fixed ``pythonscript`` which was broken by last release

0.7.1 - Morcheeba
=================

- rework the way script are executed to be possible to call them from Python easly

0.7 - 13/05/12 - Electric Guest
===============================

- move weblib to its own repository
- add support for ``is``
- added ``isinstance`` and ``issubclass``
- rework the translation for python to pythonjs
- improved generated code
- full support of exception (typed and named)
- added a set of reference transaltion ``tests/python-to-js/``


0.6.1 - 13/05/12 - Open up
==========================

- added ``getattr`` and ``setattr``

0.6 - 13/05/09 - Dispatch
=========================

- added data descriptors
- added metaclasses functions and ``type`` as a class contructor
- args and kwargs in called are respectively list and dictionary instead of javascript objects

0.5 - 13/04/01 - Lazy labor
===========================

- improvements in jquery bindings
- add minimal support for exceptions
- better support for loops
- introduce a builtins.py file
- renamed the compiled python runtime file to pythonscript.js
- booleans
- minimal list/dict/str but not fully compatible with CPython
- ``get_attribute`` support now inhertance but still not as CPython
- new special function ``var(spam, egg)`` that is translated to ``var spam, egg;``
- new ``range`` that is compatible with for loop
- several fixes in the compilation
- `sudo python <http://amirouche.github.io/sudo-python/>`_

0.4 - tldr
==========

- lazy for loop implementation (only used in pythonjs now)
- while loops
- fixing some callbacks in jquery bindings with ``adapt_arguments``

0.3 - 13/03/31
==============

- support of python(positional, arguments, key=word, *args, **kwargs), it doesn't work in callbacks

0.2 - acid lemon
================

- positional arguments
- inheritance with custom mro


0.1 - happy hacking
===================

Sometime ago I started a quest to find the best solution to do Python in the browser. My
`first idea <https://bitbucket.org/amirouche/nomad-old>`_ was to create a browser in Python thinking
that it would be easy to embedded Python in a Python browser but it's actually there is no trivial way
to sandbox Python. Building a HTML renderer is not trivial too. Then I started to dig what existed and
discovered that most of the implementation were using javascript to bridge the gap between Python's
object oriented semantic and Javascript's one, whatever the mode: compiled or interpreted. Not happy
with what was available I started `an implementation <https://bitbucket.org/amirouche/subscript>`_
following the same route, I think I tried it twice. First time I started with Google Closure then
using requirejs and Classy. The good news is I know javascript better the bad news was none really
worked. Then Brython came, I started again to think about the problem. Do I really need to write it in
Javascript? I've ditched PyPy before because RPython targets typed languages so it wasn't good for
Javascript, but the method still holds, after reading again
:download:`one of the best ressource regarding PyPy <https://github.com/amirouche/notes/raw/master/source/_static/pygirl-bruni-2009.pdf>`
I've started a new implementation that I called `PythonScript <http://apppyjs.appspot.com/>`_. It's
intersting enough because the core is fully written in Python and it quite easier to write than the
other solutions, I've put less the first release took me less than 25 hours.

Right now is rough around the edge. Abstract syntax tree API aka. ``ast`` module beauty as no other, but it works enough.
