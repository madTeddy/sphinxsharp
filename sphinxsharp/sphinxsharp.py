"""
    CSharp (С#) domain for sphinx
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Sphinxsharp Lite (with default styling)

    :copyright: Copyright 2021 by MadTeddy
"""

import re
import warnings

from os import path

from collections import defaultdict, namedtuple

from docutils import nodes
from docutils.parsers.rst import directives, Directive

from sphinx.locale import get_translation
from sphinx.domains import Domain, Index, ObjType
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.util.docfields import DocFieldTransformer
from sphinx.util.nodes import make_refnode
from sphinx import addnodes
from sphinx.util.fileutil import copy_asset

MODIFIERS = ('public', 'private', 'protected', 'internal',
             'static', 'sealed', 'abstract', 'const', 'partial',
             'readonly', 'virtual', 'extern', 'new', 'override',
             'unsafe', 'async', 'event', 'delegate')
VALUE_KEYWORDS = ('char', 'ulong', 'byte', 'decimal',
                  'double', 'bool', 'int', 'null', 'sbyte',
                  'float', 'long', 'object', 'short', 'string',
                  'uint', 'ushort', 'void')
PARAM_MODIFIERS = ('ref', 'out', 'params')

MODIFIERS_RE = '|'.join(MODIFIERS)
PARAM_MODIFIERS_RE = '|'.join(PARAM_MODIFIERS)

TYPE_SIG_RE = re.compile(r'^((?:(?:' + MODIFIERS_RE
                         + r')\s+)*)?(\w+)\s([\w\.]+)(?:<(.+)>)?(?:\s?\:\s?(.+))?$')
REF_TYPE_RE = re.compile(r'^(?:(new)\s+)?([\w\.]+)\s*(?:<(.+)>)*(\[\])*\s?(?:\((.*)\))?$')
METHOD_SIG_RE = re.compile(r'^((?:(?:' + MODIFIERS_RE
                           + r')\s+)*)?([^\s=\(\)]+\s+)?([^\s=\(\)]+)\s?(?:\<(.+)\>)?\s?(?:\((.+)*\))$')
PARAM_SIG_RE = re.compile(r'^(?:(?:(' + PARAM_MODIFIERS_RE + r')\s)*)?([^=]+)\s+([^=]+)\s*(?:=\s?(.+))?$')
VAR_SIG_RE = re.compile(r'^((?:(?:' + MODIFIERS_RE + r')\s+)*)?([^=]+)\s+([^\s=]+)\s*(?:=\s*(.+))?$')
PROP_SIG_RE = re.compile(r'^((?:(?:' + MODIFIERS_RE
                         + r')\s+)*)?(.+)\s+([^\s]+)\s*(?:{(\s*get;\s*)?((?:'
                         + MODIFIERS_RE + r')?\s*set;\s*)?})$')
ENUM_SIG_RE = re.compile(r'^((?:(?:' + MODIFIERS_RE + r')\s+)*)?(?:enum)\s?(\w+)$')

_ = get_translation('sphinxsharp')


class CSharpObject(ObjectDescription):
    PARENT_ATTR_NAME = 'sphinxsharp:parent'
    PARENT_TYPE_NAME = 'sphinxsharp:type'

    ParentType = namedtuple('ParentType', ['parent', 'name', 'type', 'override'])

    option_spec = {
        'noindex': directives.flag
    }

    def __init__(self, *args, **kwargs):
        super(CSharpObject, self).__init__(*args, **kwargs)
        self.parentname_set = None
        self.parentname_saved = None

    def run(self):
        if ':' in self.name:
            self.domain, self.objtype = self.name.split(':', 1)
        else:
            self.domain, self.objtype = '', self.name
        self.indexnode = addnodes.index(entries=[])

        node = addnodes.desc()
        node.document = self.state.document
        node['domain'] = self.domain

        node['classes'].append('csharp')

        node['objtype'] = node['desctype'] = self.objtype
        node['noindex'] = noindex = ('noindex' in self.options)

        self.names = []
        signatures = self.get_signatures()
        for i, sig in enumerate(signatures):
            beforesignode = EmptyNode()
            node.append(beforesignode)

            signode = addnodes.desc_signature(sig, '')
            signode['first'] = False
            node.append(signode)
            self.before_sig(beforesignode)
            try:
                name = self.handle_signature(sig, signode)
            except ValueError:
                signode.clear()
                signode += addnodes.desc_name(sig, sig)
                continue
            if name not in self.names:
                self.names.append(name)
                if not noindex:
                    self.add_target_and_index(name, sig, signode)

            aftersignode = EmptyNode()
            node.append(aftersignode)
            self.after_sig(aftersignode)

        contentnode = addnodes.desc_content()
        node.append(contentnode)
        self.before_content_node(contentnode)
        if self.names:
            self.env.temp_data['object'] = self.names[0]
        self.before_content()
        self.state.nested_parse(self.content, self.content_offset, contentnode)
        self.after_content_node(contentnode)
        DocFieldTransformer(self).transform_all(contentnode)
        self.env.temp_data['object'] = None
        self.after_content()
        return [self.indexnode, node]

    def before_sig(self, signode):
        """
        Called before main ``signode`` appends
        """
        pass

    def after_sig(self, signode):
        """
        Called after main ``signode`` appends
        """
        pass

    def before_content_node(self, node):
        """
        Get ``contentnode`` before main content will append
        """
        pass

    def after_content_node(self, node):
        """
        Get ``contentnode`` after main content was appended
        """
        pass

    def before_content(self):
        obj = self.env.temp_data['object']
        if obj:
            self.parentname_set = True
            self.parentname_saved = self.env.ref_context.get(self.PARENT_ATTR_NAME)
            self.env.ref_context[self.PARENT_ATTR_NAME] = obj
        else:
            self.parentname_set = False

    def after_content(self):
        if self.parentname_set:
            self.env.ref_context[self.PARENT_ATTR_NAME] = self.parentname_saved

    def has_parent(self):
        return self._check_parent(self.PARENT_ATTR_NAME)

    def has_parent_type(self):
        return self._check_parent(self.PARENT_TYPE_NAME)

    def _check_parent(self, attr):
        return attr in self.env.ref_context and \
               self.env.ref_context[attr] is not None

    def get_parent(self):
        return self.env.ref_context.get(self.PARENT_ATTR_NAME)

    def get_type_parent(self):
        return self.env.ref_context.get(self.PARENT_TYPE_NAME)

    def get_index_text(self, sig, name, typ):
        raise NotImplementedError('Must be implemented in subclass')

    def parse_signature(self, sig):
        raise NotImplementedError('Must be implemented in subclass')

    def add_target_and_index(self, name, sig, signode):
        objname, objtype = self.get_obj_name(sig)
        type_parent = self.get_type_parent() if self.has_parent_type() else None
        if self.objtype != 'type' and type_parent:
            self.env.ref_context[self.PARENT_ATTR_NAME] = '{}{}'.format(type_parent.parent + '.' \
                                                                         if type_parent.parent else '',
                                                                        type_parent.name)
            name = self.get_fullname(objname)
            self.names.clear()
            self.names.append(name)
        anchor = '{}-{}'.format(self.objtype, name)
        if anchor not in self.state.document.ids:
            signode['names'].append(anchor)
            signode['ids'].append(anchor)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)

            objects = self.env.domaindata['sphinxsharp']['objects']
            key = (self.objtype, name)
            if key in objects:
                warnings.warn('duplicate description of {}, other instance in {}'.format(
                    key, self.env.doc2path(objects[key][0])), Warning)
            objects[key] = (self.env.docname, 'delegate' if self.objtype == 'method' else objtype)
        index_text = self.get_index_text(sig, objname, objtype)
        if index_text:
            parent = self.get_parent() if self.has_parent() else None
            if type_parent and type_parent.override and type_parent.name != objname:
                type_parent = self.ParentType(parent=type_parent.parent, name=type_parent.name, type=type_parent.type,
                                              override=None)
            index_format = '{parent} (C# {namespace});{text}' \
                if (type_parent and type_parent.parent and (type_parent.name == objname and self.objtype == 'type') \
                    and not type_parent.override) or (parent and not type_parent) \
                else '{name} (C# {type} {in_text} {parent});{text}' if type_parent and type_parent.name else '{text}'
            self.indexnode['entries'].append(('single', index_format.format(
                parent=type_parent.parent if type_parent else parent if parent else '',
                namespace=_('namespace'),
                text=index_text,
                name=type_parent.override if type_parent and type_parent.override \
                else type_parent.name if type_parent else '',
                type=_(type_parent.type) if type_parent else '',
                in_text=_('in')
            ), anchor, None, None))

    def get_fullname(self, name):
        fullname = '{parent}{name}'.format(
            parent=self.get_parent() + '.' if self.has_parent() else '', name=name)
        return fullname

    def get_obj_name(self, sig):
        raise NotImplementedError('Must be implemented in subclass')

    def append_ref_signature(self, typname, signode, append_generic=True):
        match = REF_TYPE_RE.match(typname.strip())
        if not match:
            raise Exception('Invalid reference type signature. Got: {}'.format(typname))
        is_new, name, generic, is_array, constr = match.groups()
        if is_new:
            signode += addnodes.desc_type(text='new')
            signode += nodes.Text(' ')
        types = name.split('.')
        explicit_path = []
        i = 1
        for t in types:
            styp = t.strip()
            explicit_path.append(styp)
            refnode = addnodes.pending_xref('', refdomain='sphinxsharp', reftype=None,
                                                            reftarget=styp, modname=None, classname=None)
            if not self.has_parent():
                refnode[self.PARENT_ATTR_NAME] = None
            else:
                refnode[self.PARENT_ATTR_NAME] = self.get_parent()
            if len(explicit_path) > 1:
                target_path = '.'.join(explicit_path[:-1])
                type_par = self.get_type_parent() if self.has_parent_type() else None
                refnode[self.PARENT_ATTR_NAME] = (type_par.parent + '.' \
                                                    if type_par and type_par.parent \
                                                    else '') + target_path
            refnode += addnodes.desc_type(text=styp)
            signode += refnode
            if i < len(types):
                signode += nodes.Text('.')
                i += 1
        if append_generic and generic:
            signode += nodes.Text('<')
            gen_groups = split_sig(generic)
            i = 1
            for g in gen_groups:
                self.append_ref_signature(g, signode, append_generic)
                if i < len(gen_groups):
                    signode += nodes.Text(', ')
                    i += 1
            signode += nodes.Text('>')
        if is_array:
            signode += nodes.Text('[]')
        if constr is not None:
            signode += nodes.Text('()')


class CSharpType(CSharpObject):
    option_spec = {
        **CSharpObject.option_spec,
        'nonamespace': directives.flag,
        'parent': directives.unchanged
    }

    def before_sig(self, signode):
        if 'nonamespace' not in self.options and self.has_parent():
            add_description(signode, _('namespace'), self.get_parent())

    def handle_signature(self, sig, signode):
        mod, typ, name, generic, inherits = self.parse_signature(sig)
        signode += addnodes.desc_type(text='{}'.format(mod if mod else 'private'))
        signode += nodes.Text(' ')
        signode += addnodes.desc_type(text='{}'.format(typ))
        signode += nodes.Text(' ')
        signode += addnodes.desc_name(text=name)
        if generic:
            signode += nodes.Text('<{}>'.format(generic))
        if inherits:
            signode += nodes.Text(' : ')

            inherit_types = split_sig(inherits)
            i = 1
            for t in inherit_types:
                self.append_ref_signature(t, signode)
                if i < len(inherit_types):
                    signode += nodes.Text(', ')
                    i += 1

        opt_parent = self.options['parent'] if 'parent' in self.options else None
        form = '{}.{}' if self.has_parent() and opt_parent else '{}{}'
        parent = form.format(self.get_parent() if self.has_parent() else '', opt_parent if opt_parent else '')
        self.env.ref_context[CSharpObject.PARENT_TYPE_NAME] = self.ParentType(
            parent=parent, name=name, type=typ, override=opt_parent)
        if opt_parent:
            self.env.ref_context[self.PARENT_ATTR_NAME] = parent
        return self.get_fullname(name)

    def get_index_text(self, sig, name, typ):
        rname = '{} (C# {})'.format(name, _(typ))
        return rname

    def parse_signature(self, sig):
        match = TYPE_SIG_RE.match(sig.strip())
        if not match:
            raise Exception('Invalid type signature. Got: {}'.format(sig))
        mod, typ, names, generic, inherits = match.groups()
        return mod, typ.strip(), names, generic, inherits

    def get_obj_name(self, sig):
        _, typ, name, _, _ = self.parse_signature(sig)
        return name, typ


class CSharpEnum(CSharpObject):
    option_spec = {**CSharpObject.option_spec, 'values': directives.unchanged_required,
                   **dict(zip([('val(' + str(i) + ')') for i in range(1, 21)],
                              [directives.unchanged] * 20))}

    def handle_signature(self, sig, signode):
        mod, name = self.parse_signature(sig)
        if mod:
            signode += addnodes.desc_type(text='{}'.format(mod.strip()))
            signode += nodes.Text(' ')
        signode += addnodes.desc_type(text='enum')
        signode += nodes.Text(' ')
        signode += addnodes.desc_name(text='{}'.format(name.strip()))
        return self.get_fullname(name)

    def after_content_node(self, node):
        options = self.options['values'].split()
        add_description(node, _('values').title(), ', '.join(options))
        options_values = list(value for key, value in self.options.items() \
                              if key not in ('noindex', 'values') and value)
        if not options_values:
            return
        i = 0
        for vname in options:
            if i < len(options_values):
                add_description(node, vname, options_values[i])
                i += 1

    def parse_signature(self, sig):
        match = ENUM_SIG_RE.match(sig.strip())
        if not match:
            raise Exception('Invalid enum signature. Got: {}'.format(sig))
        mod, name = match.groups()
        return mod, name.strip()

    def get_index_text(self, sig, name, typ):
        rname = '{} (C# {})'.format(name, _('enum'))
        return rname

    def get_obj_name(self, sig):
        _, name = self.parse_signature(sig)
        return name, 'enum'


class CSharpVariable(CSharpObject):

    _default = ''

    def handle_signature(self, sig, signode):
        mod, typ, name, self._default = self.parse_signature(sig)
        signode += addnodes.desc_type(text='{}'.format(mod if mod else 'private'))
        signode += nodes.Text(' ')
        self.append_ref_signature(typ, signode)
        signode += nodes.inline(text=' ')
        signode += addnodes.desc_addname(text='{}'.format(name))
        return self.get_fullname(name)

    def before_content_node(self, node):
        if self._default:
            add_description(node, _('value').title(), self._default)

    def parse_signature(self, sig):
        match = VAR_SIG_RE.match(sig.strip())
        if not match:
            raise Exception('Invalid variable signature. Got: {}'.format(sig))
        mod, typ, name, default = match.groups()
        return mod, typ.strip(), name.strip(), default

    def get_index_text(self, sig, name, typ):
        rname = '{} (C# {})->{}'.format(name, _('variable'), typ)
        return rname

    def get_obj_name(self, sig):
        _, typ, name, _ = self.parse_signature(sig)
        return name, typ


class CSharpProperty(CSharpObject):

    def handle_signature(self, sig, signode):
        mod, typ, name, getter, setter = self.parse_signature(sig)
        signode += addnodes.desc_type(text='{}'.format(mod if mod else 'private'))
        signode += nodes.Text(' ')
        self.append_ref_signature(typ, signode)
        signode += nodes.inline(text=' ')
        signode += addnodes.desc_addname(text='{}'.format(name))
        signode += nodes.Text(' { ')
        accessors = []
        if getter:
            accessors.append('get;')
        if setter:
            accessors.append(setter.strip())
        signode += addnodes.desc_type(text=' '.join(accessors))
        signode += nodes.Text(' } ')
        return self.get_fullname(name)

    def parse_signature(self, sig):
        match = PROP_SIG_RE.match(sig.strip())
        if not match:
            raise Exception('Invalid property signature. Got: {}'.format(sig))
        mod, typ, name, getter, setter = match.groups()
        return mod, typ.strip(), name.strip(), getter, setter

    def get_index_text(self, sig, name, typ):
        rname = '{} (C# {})->{}'.format(name, _('property'), typ)
        return rname

    def get_obj_name(self, sig):
        _, typ, name, _, _ = self.parse_signature(sig)
        return name, typ


class CSharpMethod(CSharpObject):
    option_spec = {**CSharpObject.option_spec,
                    'returns': directives.unchanged,
                   **dict(zip([('param(' + str(i) + ')') for i in range(1, 8)],
                              [directives.unchanged] * 7))}

    _params_list = ()

    def handle_signature(self, sig, signode):
        mod, typ, name, generic, params = self.parse_signature(sig)
        signode += addnodes.desc_type(text='{}'.format(mod.strip() if mod else 'private'))
        signode += nodes.Text(' ')
        self.append_ref_signature(typ if typ else name, signode)
        signode += nodes.inline(text=' ')
        if typ:
            signode += addnodes.desc_addname(text='{}'.format(name))
        if generic:
            signode += nodes.Text('<{}>'.format(generic))
        param_node = addnodes.desc_parameterlist()
        if params:
            self._params_list = self._get_params(params)
            for (pmod, ptyp, pname, pvalue) in self._params_list:
                pnode = addnodes.desc_parameter()
                if pmod:
                    pnode += addnodes.desc_type(text='{}'.format(pmod))
                    pnode += nodes.Text(' ')
                self.append_ref_signature(ptyp, pnode)
                pnode += nodes.Text(' ')
                pnode += addnodes.desc_addname(text='{}'.format(pname))
                if pvalue:
                    pnode += nodes.Text(' = ')
                    self.append_ref_signature(pvalue, pnode)
                param_node += pnode
        signode += param_node
        return self.get_fullname(name)

    def before_content_node(self, node):
        if 'returns' in self.options:
            add_description(node, _('returns').title(), self.options['returns'])

    def after_content_node(self, node):
        options_values = list(value for key, value in self.options.items() if key != 'noindex')
        i = 0
        for (_, _, pname, _) in self._params_list:
            if i < len(options_values):
                add_description(node, pname, options_values[i], lower=True)
                i += 1

    def after_content(self):
        super().after_content()
        if self._params_list is not None and len(self._params_list) > 0:
            del self._params_list

    def parse_signature(self, sig):
        match = METHOD_SIG_RE.match(sig.strip())
        if not match:
            raise Exception('Invalid method signature. Got: {}'.format(sig))
        mod, typ, name, generic, params = match.groups()
        return mod, typ, name.strip(), generic, params

    @staticmethod
    def parse_param_signature(sig):
        match = PARAM_SIG_RE.match(sig.strip())
        if not match:
            raise Exception('Invalid parameter signature. Got: {}'.format(sig))
        mod, typ, name, value = match.groups()
        return mod, typ.strip(), name.strip(), value

    def _get_params(self, params):
        if not params:
            return None
        result = []
        params_group = split_sig(params)
        for param in params_group:
            pmod, ptyp, pname, pvalue = self.parse_param_signature(param)
            result.append((pmod, ptyp, pname, pvalue))
        return result

    def get_index_text(self, sig, name, typ):
        params_text = ''
        if self._params_list:
            names = [pname
                     for _, _, pname, _
                     in self._params_list]
            params_text = '({})'.format(', '.join(names))
        if typ:
            rname = '{}{} (C# {})->{}'.format(name, params_text, _('method'), typ)
        else:
            rname = '{}{} (C# {})->{}'.format(name, params_text, _('constructor'), name)
        return rname

    def get_obj_name(self, sig):
        _, typ, name, _, _ = self.parse_signature(sig)
        return name, typ


class CSharpNamespace(Directive):
    required_arguments = 1

    def run(self):
        env = self.state.document.settings.env
        namespace = self.arguments[0].strip()
        if namespace is None:
            env.ref_context.pop(CSharpObject.PARENT_ATTR_NAME, None)
        else:
            env.ref_context[CSharpObject.PARENT_ATTR_NAME] = namespace
        return []

    
class CSharpEndType(Directive):
    required_arguments = 0

    def run(self):
        env = self.state.document.settings.env
        if CSharpObject.PARENT_TYPE_NAME in env.ref_context:
            env.ref_context.pop(CSharpObject.PARENT_TYPE_NAME, None)
        return []


class CSharpXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        refnode[CSharpObject.PARENT_ATTR_NAME] = env.ref_context.get(
            CSharpObject.PARENT_ATTR_NAME)
        return super(CSharpXRefRole, self).process_link(env, refnode,
                                                        has_explicit_title, title, target)


class CSharpIndex(Index):
    name = 'csharp'
    localname = 'CSharp Index'
    shortname = 'CSharp'

    def generate(self, docnames=None):
        content = defaultdict(list)

        objects = self.domain.get_objects()
        objects = sorted(objects, key=lambda obj: obj[0])

        for name, dispname, objtype, docname, anchor, _ in objects:
            content[dispname.split('.')[-1][0].lower()].append(
                (dispname, 0, docname, anchor, docname, '', objtype))

        content = sorted(content.items())

        return content, True


class CSharpDomain(Domain):
    name = 'sphinxsharp'
    label = 'C#'

    roles = {
        'type': CSharpXRefRole(),
        'var': CSharpXRefRole(),
        'prop': CSharpXRefRole(),
        'meth': CSharpXRefRole(),
        'enum': CSharpXRefRole()
    }

    object_types = {
        'type': ObjType(_('type'), 'type', 'obj'),
        'variable': ObjType(_('variable'), 'var', 'obj'),
        'property': ObjType(_('property'), 'prop', 'obj'),
        'method': ObjType(_('method'), 'meth', 'obj'),
        'enum': ObjType(_('enum'), 'enum', 'obj')
    }

    directives = {
        'namespace': CSharpNamespace,
        'end-type': CSharpEndType,
        'type': CSharpType,
        'variable': CSharpVariable,
        'property': CSharpProperty,
        'method': CSharpMethod,
        'enum': CSharpEnum
    }

    indices = {
        CSharpIndex
    }

    initial_data = {
        'objects': {}  # (objtype, name) -> (docname, objtype(class, struct etc.))
    }

    def clear_doc(self, docname):
        for (objtype, name), (doc, _) in self.data['objects'].copy().items():
            if doc == docname:
                del self.data['objects'][(objtype, name)]

    def get_objects(self):
        for (objtype, name), (docname, _) in self.data['objects'].items():
            yield (name, name, objtype, docname, '{}-{}'.format(objtype, name), 0)

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        targets = get_targets(target, node)

        objects = self.data['objects']
        roletypes = self.objtypes_for_role(typ)

        types = ('type', 'enum', 'method') if typ is None else roletypes

        for t in targets:
            for objtyp in types:
                key = (objtyp, t)
                if key in objects:
                    obj = objects[key]
                    if typ is not None: 
                        role = self.role_for_objtype(objtyp)
                        node['reftype'] = role
                    return make_refnode(builder, fromdocname, obj[0],
                                        '{}-{}'.format(objtyp, t), contnode,
                                        '{} {}'.format(obj[1], t))
        return None

    def merge_domaindata(self, docnames, otherdata):
        for (objtype, name), (docname, typ) in otherdata['objects'].items():
            if docname in docnames:
                self.data['objects'][(objtype, name)] = (docname, typ)

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        for typ in self.roles:
            xref = self.resolve_xref(env, fromdocname, builder, typ,
                                     target, node, contnode)
            if xref:
                return [('sphinxsharp:{}'.format(typ), xref)]

        return []


class EmptyNode(nodes.Element):

    def __init__(self, rawsource='', *children, **attributes):
        super().__init__(rawsource, *children, **attributes)

    @staticmethod
    def visit_html(self, node): pass

    @staticmethod
    def depart_html(self, node): pass


def split_sig(params):
    if not params:
        return None
    result = []
    current = ''
    level = 0
    for char in params:
        if char in ('<', '{', '['):
            level += 1
        elif char in ('>', '}', ']'):
            level -= 1
        if char != ',' or level > 0:
            current += char
        elif char == ',' and level == 0:
            result.append(current)
            current = ''
    if current.strip() != '':
        result.append(current)
    return result

def get_targets(target, node):
    targets = [target]
    if node[CSharpObject.PARENT_ATTR_NAME] is not None:
        parts = node[CSharpObject.PARENT_ATTR_NAME].split('.')
        while parts:
            targets.append('{}.{}'.format('.'.join(parts), target))
            parts = parts[:-1]
    return targets

def add_description(node, title, text, **kwargs):
    desc = nodes.container()
    if 'lower' not in kwargs or not kwargs['lower']:
        title = title[0].title() + title[1:]
    desc += nodes.strong(text=title + ':')
    desc += nodes.Text(' ')
    desc += nodes.Text(text)
    node += desc

def setup(app):
    package_dir = path.abspath(path.dirname(__file__))

    app.add_domain(CSharpDomain)
    app.add_node(EmptyNode, html=(EmptyNode.visit_html, EmptyNode.depart_html))

    locale_dir = path.join(package_dir, 'locales')
    app.add_message_catalog('sphinxsharp', locale_dir)
    return {
        'version': '1.0.2',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
