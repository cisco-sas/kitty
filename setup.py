from setuptools import setup, find_packages
import os
import sys


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = '0.6.9'
AUTHOR = 'Cisco SAS team'
EMAIL = 'kitty-fuzzer@googlegroups.com'
URL = 'https://github.com/cisco-sas/kitty.git'
DESCRIPTION = read('README.rst')
KEYWORDS = 'fuzz,fuzzing,framework,sulley,kitty,kittyfuzzer,security'

# python 3 - install only the remote package
if sys.version_info >= (3,):
    setup(
        name='kittyfuzzer-remote',
        version=VERSION,
        description='Kitty remote agent for python 3',
        long_description=DESCRIPTION,
        author=AUTHOR,
        author_email=EMAIL,
        url=URL,
        packages=['kitty/remote'],
        install_requires=['docopt', 'six', 'requests'],
        keywords=KEYWORDS,
    )
# python 2 - install full kitty framework
else:
    setup(
        name='kittyfuzzer',
        version=VERSION,
        description='Kitty fuzzing framework',
        long_description=DESCRIPTION,
        author=AUTHOR,
        author_email=EMAIL,
        url=URL,
        packages=find_packages(),
        install_requires=['docopt', 'bitstring', 'six', 'requests'],
        keywords=KEYWORDS,
        entry_points={
            'console_scripts': [
                'kitty-web-client=bin.kitty_web_client:_main',
                'kitty-template-tester=bin.kitty_template_tester:_main',
                'kitty-tool=bin.kitty_tool:_main',
            ]
        },
        package_data={'kitty': ['interfaces/web/static/*', 'interfaces/web/images/*']}
    )
