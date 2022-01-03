import json
from bdsim import *
import sys

def bdload(bd, filename = None, globals={}, **kwargs):

    print('in bdrun', sys.argv)

    if filename is None:
        filename = sys.argv[-1]

    # load the JSON file

    # TODO should have argparser, need to be careful how it interacts with bdsim
    #  argparser
    with open(filename, 'r') as f:
        model = json.load(f)

    # results is a dict with elements: blocks, wires

    # load the blocks and build mappings

    # blocks and wires have unique ids.
    #  block input and output ports have an associated socket id
    #  each wire is specified by the socket ids of its start and end

    output_dict = {}      # block output id -> Plug
    connector_dict = {}  # connector block: input socket -> output socket
    wire_dict = {}       # wire: start socket t-> end socket
    block_dict = {}      # block: block id -> Block instance

    # create a dictionary of all blocks
    for block in model['blocks']:
        # Connector block, create a dict that maps end port id to start port id
        if block['block_type'] == "CONNECTOR":
            start = block['inputs'][0]['id']
            end = block['outputs'][0]['id']
            connector_dict[end] = start

        elif block['block_type'] == "MAIN":
            continue  # nothing to be done

        else:
            # regular bdsim Block
            block_init = bd.__dict__[block['block_type']]  # block class
            params = dict(block['parameters'])  # block params as a dict

            if verbose:
                print(f"[{block['title']}]:")
            # process the parameters
            for key, value in params.items():
                if verbose:
                    print(f"    {key}: ", end='')

                newvalue = None
                if isinstance(value, str):
                    # either an "any" type or an assignment
                    if value[0] == '=':
                        # assignment
                        try:
                            newvalue = eval(value[1:], globals(), globalvars)
                        except (ValueError, TypeError, NameError, SyntaxError):
                            print(fg('red'))
                            print(f"bdload: error resolving parameter {key}: {value} for block [{block['title']}]")
                            print(attr(0))
                            raise RuntimeError(f"cannot instantiate block {block['title']} - bad parameters?")
                    else:
                        # assume it's an "any" type, attempt to evaluate it
                        try:
                            newvalue = eval(value, globals(), globalvars)
                        except (NameError, SyntaxError):
                            pass
                    
                if newvalue is not None:
                    params[key] = newvalue
                    if verbose:
                        print(f" {value} -> {newvalue}")
                else:
                    if verbose:
                        print(f" {value}")
                    
            # instantiate the block
            try:
                if 'blockargs' in params:
                    blockargs = params['blockargs']
                    del params['blockargs']

                blockargs = blockargs or {}

                newblock = block_init(name=block['title'], **params, **blockargs)    # instantiate the block
            
            except (ValueError, TypeError, NameError, SyntaxError):
                print(fg('red'))
                print(f"bdload: error instantiating block [{block['title']}]")
                args = ', '.join([f"{arg[0]}={arg[1]}" for arg in block['parameters']])
                print(f"  {block['block_type']}({args})")
                print(attr(0))
                raise RuntimeError(f"cannot instantiate block {block['title']} - bad parameters?")

            block_dict[block['id']] = newblock # add to mapping
            for output in block['outputs']:
                # each output id is mapped to the output Plug
                output_dict[output['id']] = newblock[output['index']]

    # create a dictionary of all wires: map end id -> start id
    # end id is associated with a block input port (socket)
    # this maps to a unique output port
    for wire in model['wires']:
        start = wire['start_socket']
        end = wire['end_socket']
        wire_dict[end] = start
        
    # do the wiring
    for block in model['blocks']:
        if block['block_type'] == "CONNECTOR":
            continue

        # only process real blocks
        id = block['id']

        for input in block['inputs']:
            # for every input port
            in_id = input['id']  # get the socket id

            if in_id not in wire_dict:
                raise ValueError(f"bdload: error block [{block['title']}] has unconnected input port")

            # if input has a wire attached (should have!)
            start_id =  wire_dict[in_id]

            while start_id in connector_dict:
                start_id = wire_dict[connector_dict[start_id]]  # other side of the connector
                
            # start_id now refers to a bdsim block output
            end = block_dict[id][input['index']]  # create an output Plug
            start = output_dict[start_id]   # get Plug it goes to

            if verbose:
                print(start, ' --> ', end)
            bd.connect(start, end)

    return bd

def bdrun(T, filename = None, globals={}, **kwargs):
    sim = BDSim(**kwargs)

    bd = sim.blockdiagram()

    bd = bdload(bd, filename=filename, globals=globals, **kwargs)
    bd.compile()
    bd.report()

    print('** sim for ', T)
    sim.run(bd, T)
    sim.done(bd, block=True)
    print('** DONE')

if __name__ == "__main__":

    bdrun()
