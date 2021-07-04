import bdsim
import re
from collections import OrderedDict

re_isfield = re.compile(r'\s*:[a-zA-Z0-9_ ]+:')
re_field = re.compile(r'^\s*:(?P<field>[a-zA-Z]+)(?: +(?P<var>[a-zA-Z0-9_]+))?:(?P<body>.+)$', re.MULTILINE)

def indent(s):
    return len(s) - len(s.lstrip())

sim = bdsim.BDSim(verbose=True)

blocks = {}

fieldnames = ('param', 'type', 'input', 'output', 'varinputs')
excludevars = ('kwargs', 'inputs')

for name, block, path in sim.blocklibrary:

    # create a dict of block info
    block_info = {}
    block_info['path'] = path

    # get the docstring
    ds = block.__init__.__doc__

    # parse out all lines of the form:
    #
    #  :field var: body
    # or
    #  :field var: body with a very long description that
    #       carries over to another line or two
    fieldlines = []
    for para in ds.split('\n\n'):
        # print(para)
        # print('--')

        indent_prev = None
        infield = False

        for line in para.split('\n'):
            if len(line) == 0:
                continue
            if indent_prev is None:
                indent_prev = indent(line)
            if re_isfield.match(line) is not None:
                fieldlines.append(line.lstrip())
                infield = True
            if indent(line) > indent_prev and infield:
                fieldlines[-1] += ' ' + line.lstrip()
            if indent(line) == indent_prev:
                infield = False

    # fieldlines is a list of lines of the form
    #
    #   :field var: body
    #
    # where extension lines have been concatenated

    # create a dict of dicts
    #
    #   dict[field][var] -> body
    dict = OrderedDict()

    for line in fieldlines:
        m = re_field.match(line)
        if m is not None:
            field, var, body = m.groups()
            if var in excludevars or field not in fieldnames:
                continue
            if field not in dict:
                dict[field] = {var: body}
            else:
                dict[field][var] = body
            dict[m.group('field')]

    # now connect pairs of lines of the form
    #
    # :param X: param description
    # :type X: type description
    #
    # params[X] = (type description, param description)
    params = {}
    if 'param' in dict:
        for var, descrip in dict['param'].items():
            typ = dict['type'].get(var, None)
            params[var] = (typ, descrip)

    # now add all the other stuff we know about the block
    block_info['params'] = params
    block_info['inputs'] = dict.get('input')
    block_info['outputs'] = dict.get('output')
    block_info['varinputs'] = 'varinputs' in dict
    try:
        instance = block()
        block_info['nin'] = instance.nin
        block_info['nout'] = instance.nout
        block_info['blockclass'] = instance.blockclass
    except:

        print('couldnt instantiate ', name)
        block_info['nin'] = 1
        block_info['nout'] = 1
        blockclass = block.__base__.__name__.lower().replace('block', '')
        block_info['blockclass'] = blockclass


    blocks[name] = block_info

print(blocks)