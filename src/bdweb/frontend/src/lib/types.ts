// Types shared across the frontend, matching the backend's .bd JSON format
// and the API responses.

export interface Port {
    id: string;
    index: number;
    name?: string;
}

export interface BlockParam {
    name: string;
    value: unknown;
    type?: string;
    description?: string;
}

// A node in the diagram (one bdsim block instance)
export interface DiagramNode {
    id: string;
    block_type: string; // e.g. "GAIN"
    title: string;
    pos_x: number;
    pos_y: number;
    width: number;
    height: number;
    flipped: boolean;
    inputsNum: number;
    outputsNum: number;
    parameters: [string, unknown][];
}

// A wire connecting two ports
export interface DiagramWire {
    id: string;
    start_node: string;  // DiagramNode id
    start_port: number;  // output port index
    end_node: string;    // DiagramNode id
    end_port: number;    // input port index
}

export interface Diagram {
    blocks: DiagramNode[];
    wires: DiagramWire[];
    scene_width?: number;
    scene_height?: number;
}

// Data payload for a bdsim block node in @xyflow/svelte.
// Must intersect with Record<string,unknown> so Node<BlockData> satisfies
// the xyflow generic constraint.
export type BlockData = Record<string, unknown> & {
    label: string;
    blockType: string;
    blockClass: string;
    url?: string;
    nin: number;
    nout: number;
    inputNames: string[];
    outputNames: string[];
    params: [string, unknown][];
};

// API: block library entry
export interface BlockInfo {
    name: string;         // "GAIN"
    classname: string;    // "Gain"
    blockclass: string;   // "function" | "source" | "sink" | "transfer"
    module: string;
    package: string;
    nin: number;
    nout: number;
    inputs?: string[];
    outputs?: string[];
    params?: Record<string, { type: 'bool' | 'number' | 'str' | 'list'; default: unknown }>; // introspected
    url?: string;
}

export type BlockLibrary = Record<string, BlockInfo[]>; // blockclass → blocks
