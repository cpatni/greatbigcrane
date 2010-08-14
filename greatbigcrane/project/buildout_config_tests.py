from django.test import TestCase
from django.template import Template, RequestContext

import tempfile

from greatbigcrane.project.buildout_config import buildout_parse, BuildoutConfig, buildout_write

"""
Notes:
* *Parse simplest buildout.cfg*
* *Parse more complicated buildout.cfg*

* *Write simplest buildout.cfg*
* Write more complicated buildout.cfg
* Write config and make sure sections order is preserved
* *Write config and make sure lists of things are separated by newlines and indents properly*
"""

class BuildoutParse(TestCase):
    """Tests for buildout_parse module"""

    def test_parse_simplest_buildout(self):
        fp = mktmpcfg(simple_buildout_cfg)
        buildout_object = buildout_parse(fp.name)

        assert buildout_object['buildout']['parts'] == ''

    def test_parse_complicated_buildout(self):
        fp = mktmpcfg(complicated_buildout_cfg)
        buildout_object = buildout_parse(fp.name)

        assert buildout_object['buildout'].keys() == ['parts', 'unzip']

        assert buildout_object['buildout']['parts'] == ['eggs', 'django', 'pyzmq']

    def test_write_simplest_buildout(self):
        bc = BuildoutConfig()
        bc['buildout']['parts'] = ''
        bc['buildout']['find-links'] = 'http://pypi.python.org/simple'

        fp = tempfile.NamedTemporaryFile()

        buildout_write(fp.name, bc)

        data = fp.read()
        assert data == '''[buildout]
parts = 
find-links = http://pypi.python.org/simple

'''

    def test_write_simplest_list_buildout(self):
        bc = BuildoutConfig()
        bc['buildout']['parts'] = ''
        bc['buildout']['find-links'] = ['http://pypi.python.org/simple', 'http://python.org']

        fp = tempfile.NamedTemporaryFile()

        buildout_write(fp.name, bc)

        data = fp.read()
        assert data == '''[buildout]
parts = 
find-links = 
\thttp://pypi.python.org/simple
\thttp://python.org

'''

def mktmpcfg(cfg):
    fp = tempfile.NamedTemporaryFile()
    fp.write(cfg)
    fp.seek(0)

    return fp

simple_buildout_cfg = """[buildout]
parts = """

complicated_buildout_cfg = """[buildout]
parts = eggs django pyzmq
unzip = true

[eggs]
recipe = zc.recipe.egg
eggs =
    south==0.7.1
    IPython
extra-paths =
    ${buildout:directory}/parts/django
    ${buildout:directory}/parts/django-registration
    ${buildout:directory}/greatbigcrane
    ${buildout:directory}/parts/pyzmq

[django]
settings = development
recipe = djangorecipe
version = 1.2.1
eggs = ${eggs:eggs}
project = greatbigcrane
extra-paths = ${eggs:extra-paths}
fcgi = True
wsgi = True

[pyzmq]
recipe = zerokspot.recipe.git
repository = http://github.com/zeromq/pyzmq.git
as_egg = True"""
