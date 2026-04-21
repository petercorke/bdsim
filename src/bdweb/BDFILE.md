# `.bd` File Format

`.bd` files are JSON documents describing a block diagram. The format originates from [bdedit](https://github.com/petercorke/bdedit) and is the native load/save format for both bdedit and bdweb.

---

## Top-level structure

```json
{
    "id":             140192902056064,
    "created_by":     "bdweb",
    "creation_time":  1713600000,
    "scene_width":    7200.0,
    "scene_height":   3600.0,
    "blocks":         [ ... ],
    "wires":          [ ... ]
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique diagram ID. bdedit uses `id(self)` (Python object id); bdweb uses sequential integers. |
| `created_by` | string | Name of the application or user that saved the file. |
| `creation_time` | integer | Unix timestamp (seconds) when the file was saved. |
| `scene_width` | float | Width of the editor canvas in scene units (bdedit default: ~7200). |
| `scene_height` | float | Height of the editor canvas in scene units (bdedit default: ~3600). |
| `blocks` | array | List of block objects (see below). |
| `wires` | array | List of wire objects (see below). |

---

## Block object

Each entry in `blocks` represents one block instance.

```json
{
    "id":          140596124728768,
    "block_type":  "GAIN",
    "title":       "Gain Block",
    "pos_x":       -80.0,
    "pos_y":       -120.0,
    "width":       100,
    "height":      100,
    "flipped":     false,
    "inputsNum":   1,
    "outputsNum":  1,
    "inputs":      [ ... ],
    "outputs":     [ ... ],
    "parameters":  [ ... ]
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique block ID within the file. Used by wires to identify socket ownership. |
| `block_type` | string | bdsim block class name in upper-case, e.g. `"GAIN"`, `"SUM"`, `"LTI_SISO"`. |
| `title` | string | Human-readable display label shown in the editor. |
| `pos_x` | float | X position of the block's top-left corner in scene coordinates. |
| `pos_y` | float | Y position of the block's top-left corner in scene coordinates. Positive Y is downward. |
| `width` | integer | Block width in scene units (typically 100). |
| `height` | integer | Block height in scene units (typically 100). |
| `flipped` | boolean | When `true`, inputs appear on the right side and outputs on the left (block is mirrored). |
| `inputsNum` | integer | Number of input ports. Must equal `len(inputs)`. |
| `outputsNum` | integer | Number of output ports. Must equal `len(outputs)`. |
| `inputs` | array | Socket descriptors for input ports (see [Socket object](#socket-object)). |
| `outputs` | array | Socket descriptors for output ports (see [Socket object](#socket-object)). |
| `parameters` | array | List of `[name, value]` pairs for block constructor arguments (see [Parameters](#parameters)). |

---

## Socket object

Each block has an `inputs` array and an `outputs` array. Each element describes one port (socket).

```json
{
    "id":         140596124784720,
    "index":      0,
    "multi_wire": true,
    "position":   1,
    "socket_type": 1
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Globally unique socket ID across the entire file. Wires reference these IDs. |
| `index` | integer | Zero-based port index within this block's input or output list. |
| `multi_wire` | boolean | Whether multiple wires may connect to this socket. Always `true` in bdweb. |
| `position` | integer | Side of the block where the socket appears. `1` = left (inputs), `3` = right (outputs). Reversed when `flipped` is `true`. |
| `socket_type` | integer | `1` = input socket, `2` = output socket. |

**Position constants:**

| Value | Meaning |
|---|---|
| `1` | Left edge |
| `2` | Top edge |
| `3` | Right edge |
| `4` | Bottom edge |

---

## Wire object

Each entry in `wires` represents a directed connection from one output socket to one input socket.

```json
{
    "id":               140596130001234,
    "start_socket":     140596124784768,
    "end_socket":       140596130326800,
    "wire_type":        3,
    "custom_routing":   false,
    "wire_coordinates": []
}
```

| Field | Type | Description |
|---|---|---|
| `id` | integer | Unique wire ID within the file. |
| `start_socket` | integer | Socket ID of the **output** port this wire leaves from. Must match the `id` of an entry in some block's `outputs` array. |
| `end_socket` | integer | Socket ID of the **input** port this wire connects to. Must match the `id` of an entry in some block's `inputs` array. |
| `wire_type` | integer | Routing style. `3` = Bezier (default). Other values are bdedit-internal. |
| `custom_routing` | boolean | When `true`, `wire_coordinates` provides explicit intermediate waypoints. |
| `wire_coordinates` | array | List of `[x, y]` waypoints for custom-routed wires. Empty for auto-routed wires. |

Wires are always directed: **output → input**. A single output socket may have multiple wires fanning out; an input socket normally has exactly one wire.

---

## Parameters

The `parameters` field is a list of `[name, value]` pairs corresponding to the block's constructor keyword arguments:

```json
"parameters": [
    ["K",      10],
    ["premul", false],
    ["signs",  "+-"],
    ["N",      null]
]
```

- The order matches the block's `__init__` signature.
- `null` represents Python `None` (the parameter keeps its default).
- Supported value types: `number` (int or float), `boolean`, `string`, `null`, and JSON arrays (for list-valued parameters).

---

## Coordinate system

- The scene origin `(0, 0)` is the centre of the canvas.
- Positive X is rightward; positive Y is **downward** (matching screen coordinates).
- Block `pos_x`/`pos_y` refer to the **top-left corner** of the block.
- Scene dimensions (`scene_width`, `scene_height`) describe the total scrollable area; the visible viewport is a subset of this.

---

## Compatibility notes

- **bdweb → bdedit:** Files saved by bdweb use sequential small integers for IDs (starting at 1). bdedit uses Python `id()` values which are large integers, but bdedit accepts any integer IDs when loading.
- **bdedit → bdweb:** bdweb's backend auto-detects the wire format. Files from either tool load correctly.
- The `created_by` field is informational only and is not validated on load.
- Unknown top-level keys are ignored on load, so additional metadata can be embedded without breaking compatibility.

---

## Minimal example

A diagram with a CONSTANT source wired to a SCOPE sink:

```json
{
    "id": 1,
    "created_by": "bdweb",
    "creation_time": 1713600000,
    "scene_width": 7200.0,
    "scene_height": 3600.0,
    "blocks": [
        {
            "id": 2,
            "block_type": "CONSTANT",
            "title": "constant.0",
            "pos_x": -200.0, "pos_y": -50.0,
            "width": 100, "height": 100,
            "flipped": false,
            "inputsNum": 0, "outputsNum": 1,
            "inputs": [],
            "outputs": [
                {"id": 3, "index": 0, "multi_wire": true, "position": 3, "socket_type": 2}
            ],
            "parameters": [["value", 1]]
        },
        {
            "id": 4,
            "block_type": "SCOPE",
            "title": "scope.0",
            "pos_x": 100.0, "pos_y": -50.0,
            "width": 100, "height": 100,
            "flipped": false,
            "inputsNum": 1, "outputsNum": 0,
            "inputs": [
                {"id": 5, "index": 0, "multi_wire": true, "position": 1, "socket_type": 1}
            ],
            "outputs": [],
            "parameters": []
        }
    ],
    "wires": [
        {
            "id": 6,
            "start_socket": 3,
            "end_socket": 5,
            "wire_type": 3,
            "custom_routing": false,
            "wire_coordinates": []
        }
    ]
}
```
