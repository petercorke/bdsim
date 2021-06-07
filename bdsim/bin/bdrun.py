import json
import sys
from bdsim import *

sim = BDSim()

bd = sim.blockdiagram()

# load the JSON file
# filename = sys.argv[1]
filename = 'examples/eg1.json'

# TODO should have argparser, need to be careful how it interacts with bdsim
#  argparser
with open(filename, 'r') as f:
    model = json.load(f)

# results is a dict with elements: blocks, wires

# load the blocks and build mappings

# blocks and wires have unique ids.
#  block input and output ports have an associated socket id
#  each wire is specified by the socket ids of its start and end

input_dict = {}      # block input id -> Plug
connector_dict = {}  # connector block: input socket -> output socket
wire_dict = {}       # wire: start socket t-> end socket
block_dict = {}      # block: block id -> Block instance

# create a dictionary of all blocks
for block in model['blocks']:
    # Connector block
    if block['block_type'] == "Connector":
        start = block['inputs'][0]['id']
        end = block['outputs'][0]['id']
        connector_dict[start] = end
    
    else:
        # regular bdsim Block
        block_init = bd.__dict__[block['block_type']]  # block class
        params = dict(block['variables'])  # block params as a dict
        newblock = block_init(**params)    # instantiate the block
        block_dict[block['id']] = newblock # add to mapping
        for input in block['inputs']:
            # each input id is mapped to the input Plug
            input_dict[input['id']] = newblock[input['index']]

# create a dictionary of all wires: map start id -> list of end ids
# start id is associated with a block output port (socket)
# can be multiple wires from an output port, hence this maps to a list
for wire in model['wires']:
    start = wire['start_socket']
    end = wire['end_socket']
    if start in wire_dict:
        # subsequent entry, append to the list
        wire_dict[start].append(end)
    else:
        # first entry, a list of one
        wire_dict[start] = [end]
    

# print('blocks', block_dict)
# print('inputs', input_dict)
# print('wires', wire_dict)
# print('connectors', connector_dict)

for block in model['blocks']:
    if block['block_type'] == "Connector":
        continue

    # only process real blocks
    id = block['id']

    for output in block['outputs']:
        # for every output port
        out_id = output['id']  # get the socket id

        for end_id in wire_dict[out_id]:
            # for every wire

            # while end of wire goes to a connector, follow its output and
            # subsequent wire to the next block
            while end_id in connector_dict:
                end_id = connector_dict[end_id]  # other side of the connector
                end_id = wire_dict[end_id][0]    # other end of the wire
            
            # end_id now refers to a bdsim block
            start = block_dict[id][output['index']]  # create an output Plug
            end = input_dict[end_id]   # get Plug it goes to

            print(start, ' --> ', end)
            bd.connect(start, end)

bd.compile()
bd.report()

sim.run(bd)
bd.done(block=True)