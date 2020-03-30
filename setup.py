import sys
from os.path import dirname, join

from setuptools import find_packages, setup

EXCLUDE_FROM_PACKAGES = ['tests']
version = __import__('esi.version').__version__

if sys.version_info < (3, 4):
    sys.exit("Sorry, but we require python >= 3.4 to function")


def _parse_requirements(fh, dname):
    lines = fh.read().splitlines()
    for line in lines:
        if not line.strip():
            continue
        if line.startswith('#'):
            continue
        if line.startswith('-r'):
            new_path = line.split(' ', 1)[1]
            path = join(dname, new_path)
            new_dname = dirname(path)
            with open(path, 'r', encoding='utf-8') as fnew:
                for ret in _parse_requirements(fnew, new_dname):
                    yield ret
        else:
            yield line.strip()


def parse_requirements(fname):
    with open(fname, 'r', encoding='utf-8') as fh:
        return list(_parse_requirements(fh, dirname(fname)))


required_setup = parse_requirements('requirements.txt')

cmdclass = {}

try:
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    from sphinx.setup_command import BuildDoc
    # noinspection PyPackageRequirements, PyUnresolvedReferences
    from sphinx.ext.autodoc import ClassDocumenter

    class FakeModule(object):
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class SphinxDocs(BuildDoc):
        def run(self):
            # noinspection PyUnresolvedReferences
            from esi.helpers import load_from_spec, load_for_docs
            # noinspection PyPackageRequirements
            sys.modules['esi'] = FakeModule(ESI=load_from_spec('_latest', process_func=load_for_docs))
            super(SphinxDocs, self).run()
    cmdclass['build_sphinx'] = SphinxDocs
except ImportError:
    pass


name = 'esi-py'
author = 'ISD Thalack Dalhar'

setup(
    name=name,
    version=version,
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    include_package_data=True,
    entry_points={'console_scripts': [
        'esi-py-generate = esi.commands:generate [gen]',
    ]},
    install_requires=required_setup,
    python_requires='>=3.4',
    cmdclass=cmdclass,
    command_options={
        'build_sphinx': {
            'version': ('setup.py', version),
            'release': ('setup.py', version),
            'project': ('setup.py', name),
            'builder': ('setup.py', 'singlehtml'),
            'copyright': ('setup.py', ''),
        },
    },
    url='http:///',
    license='MIT',
    author=author,
    author_email='N/A',
    description='',
    classifiers=[
        'Development Status :: 2 - Alpha',
        'Environment :: Other Environment',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
