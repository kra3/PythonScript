#!/usr/bin/env python
import os
from subprocess import call
from StringIO import StringIO

from pythonscript.pythonjs import main as pythonjs


ROOT = os.path.abspath(os.path.dirname(__file__))

print('running pythonjs_to_javascript tests from ./pythonjs_to_js')

PYTHONJS_PATH = os.path.join(ROOT, 'pythonjs_to_js')
for name in sorted(os.listdir(PYTHONJS_PATH)):
    if name.endswith('.py'):
        compiled = '%s.js' % name
        compiled_file = '/tmp/%s' % compiled
        with open(compiled_file, 'w') as compiled:
            test = os.path.join(PYTHONJS_PATH, name)
            with open(test) as test:
                compiled.write(pythonjs(test.read()))
        result_file = '/tmp/%s.result' % name
        with open(result_file, 'w') as result:
            error = call(['nodejs', compiled_file], stdout=result)
            if error != 0:
                print('%s ERROR' % name)
                continue        
        expected = '%s.expected' % name
        expected = os.path.join(PYTHONJS_PATH, expected)
        with open(expected) as expected:
            with open(result_file) as result:
                expected = expected.read()
                result = result.read()
                if result == expected:
                    print('%s PASS' % name)
                else:
                    print('%s FAIL' % name)
    else:
        pass
