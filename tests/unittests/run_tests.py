#!/usr/bin/env python
import os
from subprocess import call
from StringIO import StringIO

from pythonscript.pythonjs import main as pythonjs
from pythonscript.pythonscript import main as pythonscript


ROOT = os.path.abspath(os.path.dirname(__file__))


# this is used only for pythonjs_to_js
def run_tests(directory, translator):
    PYTHONJS_PATH = os.path.join(ROOT, directory)
    for name in sorted(os.listdir(PYTHONJS_PATH)):
        if name.endswith('.py'):
            compiled = '%s.js' % name
            compiled_file = '/tmp/%s' % compiled
            with open(compiled_file, 'w') as compiled:
                test = os.path.join(PYTHONJS_PATH, name)
                with open(test) as test:
                    compiled.write(translator(test.read()))
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


print('running pythonjs tests from ./pythonjs_to_js')
run_tests('pythonjs_to_js', pythonjs)
print('\n')

print('running pythonscript tests from ./pythonscript')

from envoy import run

# this is used only for pythonscript tests
def run_tests(directory, translator):
    PYTHONJS_PATH = os.path.join(ROOT, directory)
    for name in sorted(os.listdir(PYTHONJS_PATH)):
        if name.endswith('.py'):
            compiled = '%s.js' % name
            compiled_file = '/tmp/%s' % compiled
            with open(compiled_file, 'w') as compiled:
                test = os.path.join(PYTHONJS_PATH, name)
                with open(test) as test:
                    compiled.write(translator(test.read()))
            r = run('cat %s/pythonscript/mockup_browser.js %s/../../pythonscript.js %s' % (ROOT, ROOT, compiled_file))
            with open('%s.exec' % compiled_file, 'w') as f:
                f.write(r.std_out)
            r = run('nodejs %s.exec' % compiled_file)
            if r.status_code != 0:
                print r.std_err
                print('%s ERROR' % name)
                continue
            with open('/tmp/%s.result' % name, 'w') as f:
                f.write(r.std_out)
            expected = '%s.expected' % name
            expected = os.path.join(PYTHONJS_PATH, expected)
            with open(expected) as expected:
                expected = expected.read()
                if r.std_out == expected:
                    print('%s PASS' % name)
                else:
                    print(r.std_err)
                    print('%s FAIL' % name)
        else:
            pass

run_tests('pythonscript', pythonscript)
