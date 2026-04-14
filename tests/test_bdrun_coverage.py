#!/usr/bin/env python3
"""
Additional tests for bdrun.py to improve coverage.

Targets:
  - bdload() with verbose=True  (lines 105-115, 216 verbose prints)
  - bdload() with a file containing a CONNECTOR block  (lines 74-79)
  - bdload() with a file containing a MAIN block  (lines 85-88)
  - bdload() with an "=expression" parameter  (line 135)
  - bdload() with globalvars  (exercises namespace)
"""
import json
import tempfile
import os
import unittest
from pathlib import Path

import bdsim
from bdsim.bdrun import bdload


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _write_json(model: dict) -> str:
    """Write a dict as a JSON file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".bd", delete=False, encoding="utf-8"
    )
    json.dump(model, tmp)
    tmp.close()
    return tmp.name


def _minimal_bd_json(*, with_connector=False, with_main=False, expr_param=False):
    """
    Build a minimal valid JSON block-diagram model.

    The model contains a CONSTANT block connected to a GAIN block connected
    to a NULL (sink) block.  Options inject additional block types for
    coverage purposes.

    All socket IDs are arbitrary integers that must be consistent within
    the model.
    """
    # socket IDs (arbitrary but internally consistent)
    c_out_id = 1000  # CONSTANT output socket
    g_in_id = 2000  # GAIN input socket
    g_out_id = 2001  # GAIN output socket
    n_in_id = 3000  # NULL input socket

    K_value = "=2+1" if expr_param else 3  # "=expr" triggers eval path

    blocks = [
        {
            "id": 100,
            "block_type": "CONSTANT",
            "title": "const",
            "pos_x": 0,
            "pos_y": 0,
            "width": 100,
            "height": 100,
            "flipped": False,
            "inputsNum": 0,
            "outputsNum": 1,
            "inputs": [],
            "outputs": [{"id": c_out_id, "index": 0}],
            "parameters": [["value", 5]],
        },
        {
            "id": 200,
            "block_type": "GAIN",
            "title": "gain",
            "pos_x": 200,
            "pos_y": 0,
            "width": 100,
            "height": 100,
            "flipped": False,
            "inputsNum": 1,
            "outputsNum": 1,
            "inputs": [{"id": g_in_id, "index": 0}],
            "outputs": [{"id": g_out_id, "index": 0}],
            "parameters": [["K", K_value], ["premul", False]],
        },
        {
            "id": 300,
            "block_type": "NULL",
            "title": "null",
            "pos_x": 400,
            "pos_y": 0,
            "width": 100,
            "height": 100,
            "flipped": False,
            "inputsNum": 1,
            "outputsNum": 0,
            "inputs": [{"id": n_in_id, "index": 0}],
            "outputs": [],
            "parameters": [["nin", 1]],
        },
    ]

    wires = [
        {"start_socket": c_out_id, "end_socket": g_in_id},
        {"start_socket": g_out_id, "end_socket": n_in_id},
    ]

    if with_connector:
        # Add a CONNECTOR block that passes signal from c_out_id through to g_in_id.
        # The wire from c_out_id now ends at the connector's input.
        conn_in_id = 4000
        conn_out_id = 4001
        blocks.insert(
            1,
            {
                "id": 150,
                "block_type": "CONNECTOR",
                "title": "conn",
                "pos_x": 100,
                "pos_y": 0,
                "width": 50,
                "height": 50,
                "flipped": False,
                "inputsNum": 1,
                "outputsNum": 1,
                "inputs": [{"id": conn_in_id, "index": 0}],
                "outputs": [{"id": conn_out_id, "index": 0}],
                "parameters": [],
            },
        )
        # Rewire: c_out -> conn_in, conn_out -> g_in
        wires[0] = {"start_socket": c_out_id, "end_socket": conn_in_id}
        wires.insert(1, {"start_socket": conn_out_id, "end_socket": g_in_id})

    if with_main:
        blocks.insert(
            0,
            {
                "id": 50,
                "block_type": "MAIN",
                "title": "main",
                "pos_x": -200,
                "pos_y": 0,
                "width": 50,
                "height": 50,
                "flipped": False,
                "inputsNum": 0,
                "outputsNum": 0,
                "inputs": [],
                "outputs": [],
                "parameters": [],
            },
        )

    return {"blocks": blocks, "wires": wires}


class BdloadVerboseTest(unittest.TestCase):
    """Test bdload() with verbose=True to cover the verbose print lines."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def test_eg1_verbose(self):
        """Load the eg1 example with verbose=True."""
        file = EXAMPLES_DIR / "eg1.bd"
        bd = self.sim.blockdiagram()
        bd = bdload(bd, file, verbose=True)
        self.assertGreater(len(bd.blocklist), 0)

    def test_eg1_with_globalvars(self):
        """Load eg1.bd passing a globalvars dict (exercises the namespace path)."""
        file = EXAMPLES_DIR / "eg1.bd"
        bd = self.sim.blockdiagram()
        bd = bdload(bd, file, globalvars={"myvar": 42})
        self.assertGreater(len(bd.blocklist), 0)


class BdloadConnectorMainTest(unittest.TestCase):
    """Test bdload() with CONNECTOR and MAIN block types."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def test_with_connector_block(self):
        """CONNECTOR block type adds an entry to connector_dict (lines 74-79)."""
        model = _minimal_bd_json(with_connector=True)
        path = _write_json(model)
        try:
            bd = self.sim.blockdiagram()
            bd = bdload(bd, path, verbose=False)
            self.assertEqual(len(bd.blocklist), 3)  # CONSTANT, GAIN, NULL
        finally:
            os.unlink(path)

    def test_with_connector_block_verbose(self):
        """CONNECTOR + verbose prints the wire connections."""
        model = _minimal_bd_json(with_connector=True)
        path = _write_json(model)
        try:
            bd = self.sim.blockdiagram()
            bd = bdload(bd, path, verbose=True)
            self.assertEqual(len(bd.blocklist), 3)
        finally:
            os.unlink(path)

    def test_with_main_block(self):
        """MAIN block is skipped via 'continue' (lines 85-88)."""
        model = _minimal_bd_json(with_main=True)
        path = _write_json(model)
        try:
            bd = self.sim.blockdiagram()
            bd = bdload(bd, path)
            self.assertEqual(len(bd.blocklist), 3)
        finally:
            os.unlink(path)


class BdloadExprParamTest(unittest.TestCase):
    """Test bdload() with a parameter that starts with '=' (eval path)."""

    @classmethod
    def setUpClass(cls):
        cls.sim = bdsim.BDSim(graphics=None, progress=False, banner=False)

    def test_expr_param(self):
        """Parameter '=2+1' is eval'd to 3 (covers the assignment branch, line 135)."""
        model = _minimal_bd_json(expr_param=True)
        path = _write_json(model)
        try:
            bd = self.sim.blockdiagram()
            bd = bdload(bd, path, verbose=True)
            gain_block = bd.blocknames.get("gain")
            self.assertIsNotNone(gain_block)
            self.assertEqual(gain_block.K, 3)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
