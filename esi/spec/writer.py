import warnings
from datetime import datetime
from operator import itemgetter
from os.path import isdir
from typing import List, TextIO, Dict, Union

from esi.exceptions import MissingPackageError, InvalidSpecError
from esi.utils import to_camel_case, to_pascal_case, to_snake_case, SWAGGER_BASE_URL, SWAGGER_SPEC_URLS


def describe(obj, indent=0, short=False):
    if hasattr(obj, '__do_repr__'):
        return obj.__do_repr__(indent, short)
    return repr(obj)


def do_indent(s, width=4, first=False, blank=False, indentfirst=None):
    """Return a copy of the string with each line indented by 4 spaces. The
    first line and blank lines are not indented by default.
    :param s: The string to indent.
    :param width: Number of spaces to indent by.
    :param first: Don't skip indenting the first line.
    :param blank: Don't skip indenting empty lines.
    :param indentfirst: deprecated, see `first`.
    .. versionchanged:: 2.10
        Blank lines are not indented by default.
        Rename the ``indentfirst`` argument to ``first``.
    """
    if indentfirst is not None:
        warnings.warn(DeprecationWarning(
            'The "indentfirst" argument is renamed to "first".'
        ), stacklevel=2)
        first = indentfirst

    s += u'\n'  # this quirk is necessary for splitlines method
    indention = u' ' * width

    if blank:
        rv = (u'\n' + indention).join(s.splitlines())
    else:
        lines = s.splitlines()
        rv = lines.pop(0)

        if lines:
            rv += u'\n' + u'\n'.join(
                indention + line if line else line for line in lines
            )

    if first:
        rv = indention + rv

    return rv


class ESISpecWriter:
    def __init__(self, spec):
        self.spec = spec

    def build_environment(self, template_dirs: List[str]=None, package_names: List[str]=None):
        try:
            from jinja2 import PackageLoader, ChoiceLoader, FileSystemLoader, select_autoescape,\
                environmentfilter
            from jinja2.sandbox import SandboxedEnvironment
            from jinja2.filters import do_wordwrap as orig_do_wordwrap
        except ImportError as e:
            raise MissingPackageError("The Jinja2 package is not available, but is required to generate. "
                                      "Install esi-py with the [gen] spec (`pip install esi-py[gen]`) to "
                                      "automatically install this requirement.") from e

        @environmentfilter
        def do_wordwrap(environment, s, width=79, break_long_words=True, wrapstring=None):
            # Normal wordwrap doesn't split the content by lines, thus hitting the corner case as described in
            # textwrap.wrap's documentation.
            return '\n'.join(orig_do_wordwrap(environment, x, width=width, break_long_words=break_long_words,
                                              wrapstring=wrapstring) for x in s.splitlines())

        def do_reindent(lines, width=79, indent=4):
            length = 0
            current = []
            parts = [current]
            for line in lines.splitlines():
                length += len(line)
                if length > width:
                    current = []
                    parts.append(current)
                    length = len(line)
                current.append(line)
            return do_indent('\n'.join(
                ''.join(x).rstrip()
                for x in parts), indent)

        loaders = [PackageLoader("esi", "templates")]
        if template_dirs:
            loaders.extend(FileSystemLoader(x) for x in template_dirs[::-1] if isdir(x))
        if package_names:
            loaders.extend(PackageLoader(x, "templates") for x in package_names[::-1])
        loader = ChoiceLoader(loaders)

        env = SandboxedEnvironment(
            loader=loader,
            auto_reload=select_autoescape(['html', 'xml', 'htm']),
        )
        env.filters['describe'] = describe
        env.filters['indent'] = do_indent
        env.filters['reindent'] = do_reindent
        env.filters['to_camel_case'] = to_camel_case
        env.filters['to_pascal_case'] = to_pascal_case
        env.filters['to_snake_case'] = to_snake_case
        env.filters['wordwrap_lines'] = do_wordwrap
        return env

    def render_batch(self, templates: Dict[str, Union[TextIO, bool]], encoding=None, template_dirs: List[str]=None,
                     package_names: List[str]=None, **render_kwargs):
        """

        :param templates:
        :param encoding: The encoding to use when writing to the `out` stream.
        :param template_dirs: Extra template directories to look for templates in.
        :param package_names: Extra package names to search in.
        :return:
        """
        env = self.build_environment(template_dirs, package_names)
        ret = {}

        kwargs = {
            'spec': self.spec,
            'now': datetime.utcnow()
        }
        kwargs.update(render_kwargs)
        for name, out in sorted(templates.items(), key=itemgetter(0)):
            template = env.get_template(name)
            if out:
                template.stream(kwargs).dump(out, encoding=encoding)
            else:
                out = template.render(kwargs)
            ret[name] = out
        return ret

    def render(self, template_name: str, out: TextIO=None, encoding=None, template_dirs: List[str]=None,
               package_names: List[str]=None, **render_kwargs):
        """

        :param out: The stream to write to, otherwise return the rendered template.
        :param encoding: The encoding to use when writing to the `out` stream.
        :param template_name: The template name to render.
        :param template_dirs: Extra template directories to look for templates in.
        :param package_names: Extra package names to search in.
        :return:
        """

        env = self.build_environment(template_dirs, package_names)
        template = env.get_template(template_name)

        kwargs = {
            'spec': self.spec,
            'now': datetime.utcnow()
        }
        kwargs.update(render_kwargs)

        if out:
            template.stream(kwargs).dump(out, encoding=encoding)
            return out
        else:
            return template.render(kwargs)

    def eval(self, template_name='full.py.jinja', _globals=None, template_dirs: List[str]=None,
             package_names: List[str]=None, **render_kwargs):
        """

        :param _globals:
        :param template_name: The template name to render.
        :param template_dirs: Extra template directories to look for templates in.
        :param package_names: Extra package names to search in.
        :param render_kwargs:
        :return:
        """
        klass_name = render_kwargs.get('main_class_name', 'ESI')
        _globals = _globals or globals()
        rendered = self.render(template_name, out=None, encoding=None, template_dirs=template_dirs,
                               package_names=package_names, **render_kwargs)
        _locals = {}
        exec(rendered, _globals, _locals)

        return _locals.get(klass_name), _locals

    @classmethod
    def from_spec(cls, _spec='_latest', skip_spec_check=False, **kwargs):
        """

        :param _spec: The spec to load
        :param skip_spec_check: True to not check if the check is a 'known' spec.
        :param kwargs:
        :return:
        """
        from esi.spec import ESISpec
        if not skip_spec_check and not (_spec in SWAGGER_SPEC_URLS or (_spec.startswith('v') and _spec[1:].isdigit())):
            raise InvalidSpecError(_spec)
        url = SWAGGER_BASE_URL.format(spec=_spec)

        spec = ESISpec.from_url(url, **kwargs)

        return cls(spec)
