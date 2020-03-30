from argparse import *

from os.path import join, splitext

from esi.spec import ESISpec, ESISpecWriter
from esi.utils import PathType, SWAGGER_SPEC_URLS

DEFAULT_FILES = {
    'init': '__init__.py',
    'full': 'esi.py',
    'base': 'base.py',
    'functions': 'functions.py',
    'global_data': 'global_data.py',
}

DEFAULT_TEMPLATES = {
    'init': '__init__.py.jinja',
    'full': 'full.py.jinja',
    'base': 'base.py.jinja',
    'functions': 'functions.py.jinja',
    'global_data': 'global_data.py.jinja',
}


def generate(prog=None):
    parser = ArgumentParser(description="Generate a esi-py spec file from the specified file or url", prog=prog)

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--file', '-f', '--in', help="The file containing the swagger spec to generate from",
                       type=FileType('r', encoding='utf-8'))
    group.add_argument('--url', '-u', help="The URL with the swagger spec")
    group.add_argument('--preset', '-p', help="Use one of the following 'standard' spec URLS",
                       choices=SWAGGER_SPEC_URLS)
    group.add_argument('--meta', help="Use the meta-data spec", default=False, action='store_true')

    parser.add_argument('out', help="The directory to write the generated python code to",
                        type=PathType(exists=True, type='dir'))
    parser.add_argument('--mode', '-m', default='multiple', choices=['single', 'multiple'],
                        help="Generate a single file ('single') or multiple files ('multiple', default).")
    parser.add_argument('--include-meta', help="Include the meta-spec into this output", default=False,
                        action='store_true')
    parser.add_argument('--encoding', '-e', choices=['utf-8', 'ascii'], help="Output encoding", default='utf-8')
    parser.add_argument('--namespace', '-n', default='', help="The namespace prefix to use for module imports")

    filesgroup = parser.add_argument_group("Output files", description="Override default file outputs")
    for key, value in DEFAULT_FILES.items():
        filesgroup.add_argument('--%s-out' % key, default=value, help="Override the %s module output file" % key,
                                metavar='filename')

    skipgroup = parser.add_argument_group("Skip file output", description="Skip certain files from being generated")
    for key in DEFAULT_TEMPLATES:
        skipgroup.add_argument('--skip-%s' % key, default=False, action='store_true',
                               help="Skip generating the %s module" % key)

    templategroup = parser.add_argument_group("Templates", description="Specify which templates to use for generating")
    templategroup.add_argument('--template-dir', '-T', nargs='?', help="Add these directories to the template search.",
                               type=PathType(exists=True, type='dir'))
    for key, value in DEFAULT_TEMPLATES.items():
        templategroup.add_argument('--%s-template' % key, default=value, help="Override the %s module template" % key,
                                   metavar='templatename')

    args = parser.parse_args()

    templates = {
        key: getattr(args, '%s_template' % key)
        for key in DEFAULT_TEMPLATES
    }
    fnames = {
        key: getattr(args, '%s_out' % key)
        for key in DEFAULT_FILES
    }
    skip = {
        key: getattr(args, 'skip_%s' % key, False)
        for key in DEFAULT_TEMPLATES
    }

    data = None
    if args.file:
        try:
            data = ESISpec.from_file(args.file)
            args.file.close()
        except:
            parser.error("Unable to load the specified json file")
    elif args.url:
        data = ESISpec.from_url(args.url)
    elif args.meta:
        data = ESISpec.meta_spec()
    else:
        data = ESISpec.from_spec(args.preset or '_latest')

    if args.include_meta:
        meta = ESISpec.meta_spec()
        data += meta

    writer = ESISpecWriter(data)

    if args.mode == 'single':
        fname = join(args.out, fnames['full'])
        files = {
            templates['full']: open(fname, 'wb')
        }
    else:
        files = {
            templates[key]: open(join(args.out, fnames[key]), 'wb')
            for key in DEFAULT_TEMPLATES
            if skip[key] is False and key != 'full'
        }
    modules = {
        '%s_module' % key: splitext(fnames[key])[0]
        for key in DEFAULT_TEMPLATES
        if key != 'full'
    }
    writer.render_batch(files, encoding=args.encoding, template_dirs=args.template_dir, base_namespace=args.namespace,
                        **modules)
