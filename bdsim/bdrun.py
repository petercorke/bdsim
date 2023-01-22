import json
import sys

from bdsim import BDSim
from colored import fg, attr

# available for use in bdedit expressions
import numpy as np
import math
from math import pi

try:
    from spatialmath import SE3, SE2
except:
    pass


def bdload(bd, filename, globalvars={}, verbose=False, **kwargs):
    """
    Load a block diagram model

    :param bd: block diagram to load into
    :type bd: BlockDiagram instance
    :param filename: name of JSON file to load from
    :type filename: str or Path
    :param globalvars: global variables for evaluating expressions, defaults to {}
    :type globalvars: dict, optional
    :param verbose: print parameters of all blocks as they are instantiated, defaults to False
    :type verbose: bool, optional
    :raises RuntimeError: unable to load the file
    :raises ValueError: unable to load the file
    :return: the loaded block diagram
    :rtype: BlockDiagram instance

    Block diagrams are saved as JSON files.

    A number of errors can arise at this stage:

    * a parameter starting with "=" cannot be evaluated
    * the block throws an error when instantiated, incorrect parameter values
    * unconnected input port

    If the JSON file contains a parameter of the form ``"=expression"`` then
    it is evaluated using ``eval`` with the global name space given by
    ``globalvars``.  This means that you can embed lambda expressions that use
    functions/classes defined in your module if ``globalargs`` is set to ``globals()``.

    """

    # load the JSON file
    with open(filename, "r") as f:
        model = json.load(f)

    # result is a dict with elements: blocks, wires

    # load the blocks and build mappings

    # blocks and wires have unique ids.
    #  block input and output ports have an associated socket id
    #  each wire is specified by the socket ids of its start and end

    output_dict = {}  # block output id -> Plug
    connector_dict = {}  # connector block: input socket -> output socket
    wire_dict = {}  # wire: start socket t-> end socket
    block_dict = {}  # block: block id -> Block instance

    namespace = {**globals(), **globalvars}

    # create a dictionary of all blocks
    for block in model["blocks"]:
        # Connector block, create a dict that maps end port id to start port id
        if block["block_type"] == "CONNECTOR":
            start = block["inputs"][0]["id"]
            end = block["outputs"][0]["id"]
            connector_dict[end] = start

        elif block["block_type"] == "MAIN":
            continue  # nothing to be done

        else:
            # regular bdsim Block
            block_init = bd.__dict__[block["block_type"]]  # block class
            params = dict(block["parameters"])  # block params as a dict

            if verbose:
                print(f"[{block['title']}]:")
            # process the parameters
            for key, value in params.items():
                if verbose:
                    print(f"    {key}: ", end="")

                newvalue = None
                if isinstance(value, str):
                    # either an "any" type or an assignment
                    if value[0] == "=":
                        # assignment
                        try:
                            newvalue = eval(value[1:], namespace)
                        except (ValueError, TypeError, NameError, SyntaxError):
                            print(fg("red"))
                            print(
                                f"bdload: error resolving parameter {key}: {value} for block [{block['title']}]"
                            )
                            traceback.print_exc(limit=-1, file=sys.stderr)
                            print(attr(0))
                            raise RuntimeError(
                                f"cannot instantiate block {block['title']} - bad parameters?"
                            )
                    else:
                        # assume it's an "any" type, attempt to evaluate it
                        try:
                            newvalue = eval(value, namespace)
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
                if "blockargs" in params:
                    blockargs = params["blockargs"]
                    del params["blockargs"]
                else:
                    blockargs = {}

                # blockargs = blockargs or {}

                newblock = block_init(
                    name=block["title"], **params, **blockargs
                )  # instantiate the block

            except (ValueError, TypeError, NameError, SyntaxError):
                print(fg("red"))
                print(f"bdload: error instantiating block [{block['title']}]")
                args = ", ".join([f"{arg[0]}={arg[1]}" for arg in block["parameters"]])
                print(f"  {block['block_type']}({args})")
                print(attr(0))
                raise RuntimeError(
                    f"cannot instantiate block {block['title']} - bad parameters?"
                )

            block_dict[block["id"]] = newblock  # add to mapping
            for output in block["outputs"]:
                # each output id is mapped to the output Plug
                output_dict[output["id"]] = newblock[output["index"]]

    # create a dictionary of all wires: map end id -> start id
    # end id is associated with a block input port (socket)
    # this maps to a unique output port
    for wire in model["wires"]:
        start = wire["start_socket"]
        end = wire["end_socket"]
        wire_dict[end] = start

    # do the wiring
    for block in model["blocks"]:
        if block["block_type"] == "CONNECTOR":
            continue

        # only process real blocks
        id = block["id"]

        for input in block["inputs"]:
            # for every input port
            in_id = input["id"]  # get the socket id

            if in_id not in wire_dict:
                raise ValueError(
                    f"bdload: error block [{block['title']}] has unconnected input port"
                )

            # if input has a wire attached (should have!)
            start_id = wire_dict[in_id]

            while start_id in connector_dict:
                start_id = wire_dict[
                    connector_dict[start_id]
                ]  # other side of the connector

            # start_id now refers to a bdsim block output
            end = block_dict[id][input["index"]]  # create an output Plug
            start = output_dict[start_id]  # get Plug it goes to

            if verbose:
                print(start, " --> ", end)
            bd.connect(start, end)

    return bd


def bdrun(filename=None, globals={}, **kwargs):

    if filename is None:
        filename = sys.argv[1]

    sim = BDSim(**kwargs)  # create simulator
    bd = sim.blockdiagram()  # create diagram

    bd = bdload(bd, filename=filename, globalvars=globals, **kwargs)
    bd.compile()
    bd.report()

    T = 10.0
    qout = sim.run(bd, 5, dt=0.02)  # simulate for 5s
    # sim.done(bd, block=True)
    print("bdrun exiting")


if __name__ == "__main__":
    bdrun()
