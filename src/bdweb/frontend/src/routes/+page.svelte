<script lang="ts">
	import { onMount } from 'svelte';
	import {
		SvelteFlow,
		Controls,
		Background,
		BackgroundVariant,
		MiniMap,
		type Node,
		type Edge,
		type NodeTypes,
		type Viewport
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import { api } from '$lib/api';
	import type { BlockData, BlockInfo, BlockLibrary, Diagram, DiagramNode, DiagramWire } from '$lib/types';
	import Palette from '$lib/Palette.svelte';
	import BlockNode from '$lib/BlockNode.svelte';
	import PropsPanel from '$lib/PropsPanel.svelte';

	// ── Custom node type registry ───────────────────────────────────────────
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const nodeTypes: NodeTypes = { bdsimBlock: BlockNode as any };

	// Track the SvelteFlow viewport so we can convert screen→flow coordinates
	let viewport: Viewport = $state({ x: 0, y: 0, zoom: 1 });

	/** Convert a clientX/clientY position to SvelteFlow canvas coordinates */
	function toFlowPos(el: HTMLElement, clientX: number, clientY: number) {
		const rect = el.getBoundingClientRect();
		const sx = clientX - rect.left;
		const sy = clientY - rect.top;
		return {
			x: (sx - viewport.x) / viewport.zoom,
			y: (sy - viewport.y) / viewport.zoom
		};
	}

	// ── Reactive state ($state for Svelte 5 runes) ─────────────────────────
	let nodes: Node<BlockData>[] = $state([]);
	let edges: Edge[] = $state([]);
	let library: BlockLibrary = $state({});
	let loadError = $state('');

	// Selection
	let selectedNodeId: string | null = $state(null);
	let selectedBlockType = $state('');
	let selectedBlockName = $state('');
	let selectedParams: [string, unknown][] = $state([]);
	let selectedBlockInfo: BlockInfo | null = $state(null);

	// Run results modal
	let runResult: { stdout: string; plots: string[]; error: string | null } | null = $state(null);
	let running = $state(false);

	// File path for load/save
	let filePath = $state('');

	// Incrementing counter for unique node IDs
	let nodeCounter = $state(0);

	// ── Load block library on mount ─────────────────────────────────────────
	onMount(async () => {
		try {
			library = await api.blocks();
		} catch (e) {
			loadError = String(e);
		}
	});

	// ── Convert @xyflow nodes/edges → .bd Diagram ──────────────────────────
	function toDiagram(): Diagram {
		const blocks: DiagramNode[] = nodes.map((n) => ({
			id: n.id,
			block_type: n.data.blockType,
			title: n.data.label,
			pos_x: n.position.x,
			pos_y: n.position.y,
			width: 120,
			height: 80,
			flipped: false,
			inputsNum: n.data.nin,
			outputsNum: n.data.nout,
			parameters: n.data.params ?? []
		}));

		const wires: DiagramWire[] = edges.map((e) => ({
			id: e.id,
			start_node: e.source,
			start_port: parseInt((e.sourceHandle ?? 'out-0').replace('out-', '')),
			end_node: e.target,
			end_port: parseInt((e.targetHandle ?? 'in-0').replace('in-', ''))
		}));

		return { blocks, wires };
	}

	// ── Convert .bd Diagram → @xyflow nodes/edges ──────────────────────────
	function fromDiagram(diagram: Diagram) {
		nodes = diagram.blocks.map((b) => {
			const info = blockInfoOf(b.block_type);
			return {
				id: String(b.id),
				type: 'bdsimBlock',
				position: { x: b.pos_x, y: b.pos_y },
				data: {
					label: b.title,
					blockType: b.block_type,
					blockClass: blockClassOf(b.block_type),
					url: info?.url,
					nin: b.inputsNum,
					nout: b.outputsNum,
					inputNames: [],
					outputNames: [],
					params: b.parameters
				}
			};
		});

		edges = diagram.wires.map((w) => ({
			id: String(w.id),
			source: String(w.start_node),
			sourceHandle: `out-${w.start_port}`,
			target: String(w.end_node),
			targetHandle: `in-${w.end_port}`
		}));

		// Reset counter above max id
		const numIds = diagram.blocks.map((b) => parseInt(String(b.id))).filter((n) => !isNaN(n));
		if (numIds.length) nodeCounter = Math.max(...numIds) + 1;
	}

	function blockClassOf(blockType: string): string {
		for (const [cls, blocks] of Object.entries(library)) {
			if (blocks.some((b) => b.name === blockType)) return cls.toLowerCase();
		}
		return 'other';
	}

	function blockInfoOf(blockType: string): BlockInfo | undefined {
		for (const blocks of Object.values(library)) {
			const found = blocks.find((b) => b.name === blockType);
			if (found) return found;
		}
		return undefined;
	}

	function defaultNodeName(blockType: string): string {
		const base = blockType.toLowerCase();
		const used = new Set(
			nodes
				.filter((n) => n.data.blockType === blockType)
				.map((n) => String(n.data.label).toLowerCase())
		);
		let i = 0;
		while (used.has(`${base}.${i}`)) i += 1;
		return `${base}.${i}`;
	}

	// ── Drop block from palette onto canvas ────────────────────────────────
	function onDrop(event: DragEvent) {
		event.preventDefault();
		const blockType = event.dataTransfer?.getData('application/bdsim-block');
		if (!blockType) return;

		// Find block info for nin/nout defaults
		let nin = 1, nout = 1, blockClass = 'other', blockUrl: string | undefined;
		for (const [cls, blocks] of Object.entries(library)) {
			const found = blocks.find((b) => b.name === blockType);
			if (found) {
				// nin/nout=-1 means variable port count; default to 1 until user configures
				nin = found.nin < 0 ? 1 : found.nin;
				nout = found.nout < 0 ? 1 : found.nout;
				blockClass = cls.toLowerCase();
				blockUrl = found.url;
				break;
			}
		}

		// Convert screen coordinates to flow coordinates (accounts for pan + zoom)
		const position = toFlowPos(event.currentTarget as HTMLElement, event.clientX, event.clientY);

		const id = String(++nodeCounter);
		const defaultName = defaultNodeName(blockType);
		nodes = [
			...nodes,
			{
				id,
				type: 'bdsimBlock',
				position,
				data: {
					label: defaultName,
					blockType,
					blockClass,
					url: blockUrl,
					nin,
					nout,
					inputNames: [],
					outputNames: [],
					params: []
				}
			}
		];

		// Auto-open the props flyout for newly dropped blocks
		selectedNodeId = id;
		selectedBlockType = blockType;
		selectedBlockName = defaultName;
		selectedParams = [];
		selectedBlockInfo = null;
		void (async () => {
			try {
				selectedBlockInfo = await api.blockInfo(blockType);
			} catch {}
		})();
	}

	function onDragOver(event: DragEvent) {
		event.preventDefault();
		if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
	}

	// ── Node selection → PropsPanel ────────────────────────────────────────
	async function onNodeClick({ node }: { node: Node<BlockData> }) {
		selectedNodeId = node.id;
		selectedBlockType = node.data.blockType as string;
		selectedBlockName = String(node.data.label ?? '');
		selectedParams = (node.data.params as [string, unknown][]) ?? [];
		selectedBlockInfo = null;
		try {
			selectedBlockInfo = await api.blockInfo(node.data.blockType as string);
		} catch {}
	}

	function onPaneClick() {
		selectedNodeId = null;
		selectedBlockType = '';
		selectedBlockName = '';
		selectedParams = [];
		selectedBlockInfo = null;
	}

	function onPropsApplied() {
		onPaneClick();
	}

	function onNameUpdate(name: string) {
		if (!selectedNodeId) return;
		const trimmed = name.trim();
		if (!trimmed) return;
		nodes = nodes.map((n) =>
			n.id === selectedNodeId ? { ...n, data: { ...n.data, label: trimmed } } : n
		);
		selectedBlockName = trimmed;
	}

	function onParamUpdate(params: [string, unknown][]) {
		if (!selectedNodeId) return;
		const paramMap = Object.fromEntries(params);
		const nextNin = typeof paramMap.nin === 'number' && Number.isFinite(paramMap.nin)
			? Math.max(0, Math.round(paramMap.nin))
			: null;
		const nextNout = typeof paramMap.nout === 'number' && Number.isFinite(paramMap.nout)
			? Math.max(0, Math.round(paramMap.nout))
			: null;
		nodes = nodes.map((n) =>
			n.id === selectedNodeId
				? {
					...n,
					data: {
						...n.data,
						params,
						nin: nextNin ?? n.data.nin,
						nout: nextNout ?? n.data.nout
					}
				}
				: n
		);
		selectedParams = params;
	}

	// ── Toolbar actions ────────────────────────────────────────────────────
	async function handleLoad() {
		const path = filePath.trim();
		if (!path) return;
		try {
			const diagram = await api.load(path);
			fromDiagram(diagram);
			selectedNodeId = null;
		} catch (e) {
			alert('Load failed: ' + e);
		}
	}

	async function handleSave() {
		const path = filePath.trim();
		if (!path) { alert('Enter a file path first.'); return; }
		try {
			await api.save(path, toDiagram());
		} catch (e) {
			alert('Save failed: ' + e);
		}
	}

	async function handleRun() {
		running = true;
		runResult = null;
		try {
			runResult = await api.run(toDiagram());
		} catch (e) {
			runResult = { stdout: '', plots: [], error: String(e) };
		} finally {
			running = false;
		}
	}

	function handleNew() {
		if (nodes.length && !confirm('Discard current diagram?')) return;
		nodes = [];
		edges = [];
		nodeCounter = 0;
		selectedNodeId = null;
		filePath = '';
	}
</script>

<!-- ── Layout ─────────────────────────────────────────────────────────── -->
<div class="app">
	<!-- Toolbar -->
	<header class="toolbar">
		<span class="logo">bdweb</span>

		<button onclick={handleNew}>New</button>

		<input class="filepath" bind:value={filePath} placeholder="path/to/file.bd" />
		<button onclick={handleLoad}>Load</button>
		<button onclick={handleSave}>Save</button>

		<div class="spacer" />

		<button class="run-btn" onclick={handleRun} disabled={running}>
			{running ? 'Running…' : '▶ Run'}
		</button>
	</header>

	{#if loadError}
		<div class="load-error">Backend unreachable: {loadError}. Is the FastAPI server running?</div>
	{/if}

	<!-- Main area -->
	<div class="main">
		<Palette {library} />

		<!-- Canvas -->
		<div class="canvas-wrap" role="region" ondrop={onDrop} ondragover={onDragOver}>
			<SvelteFlow
				bind:nodes
				bind:edges
				bind:viewport
				{nodeTypes}
				snapToGrid
				snapGrid={[10, 10]}
				defaultEdgeOptions={{ type: 'smoothstep' }}
				onnodeclick={onNodeClick}
				onpaneclick={onPaneClick}
			>
				<Controls />
				<Background variant={BackgroundVariant.Dots} gap={20} />
				<MiniMap />
			</SvelteFlow>

			<div class="props-flyout" class:open={!!selectedNodeId}>
				<div class="flyout-tab">Properties</div>
				<PropsPanel
					blockType={selectedBlockType}
					blockName={selectedBlockName}
					params={selectedParams}
					blockInfo={selectedBlockInfo}
					onnameupdate={onNameUpdate}
					onupdate={onParamUpdate}
					onapplied={onPropsApplied}
				/>
			</div>
		</div>
	</div>
</div>

<!-- Run results modal -->
{#if runResult}
	<div class="modal-backdrop" role="dialog" aria-modal="true">
		<div class="modal">
			<div class="modal-header">
				Run Results
				<button onclick={() => (runResult = null)}>✕</button>
			</div>

			{#if runResult.error}
				<pre class="error">{runResult.error}</pre>
			{/if}

			{#if runResult.stdout}
				<pre class="stdout">{runResult.stdout}</pre>
			{/if}

			{#if runResult.plots.length}
				<div class="plots">
					{#each runResult.plots as src}
						<img src="data:image/png;base64,{src}" alt="simulation plot" />
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	:global(body, html) { margin: 0; padding: 0; height: 100%; font-family: system-ui, sans-serif; }

	.app {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	/* Toolbar */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		background: #1e293b;
		color: white;
		z-index: 10;
	}
	.logo { font-weight: 800; font-size: 16px; margin-right: 8px; color: #7dd3fc; }
	.toolbar button {
		background: #334155;
		color: white;
		border: 1px solid #475569;
		border-radius: 4px;
		padding: 4px 10px;
		cursor: pointer;
		font-size: 13px;
	}
	.toolbar button:hover { background: #475569; }
	.toolbar button:disabled { opacity: 0.5; cursor: not-allowed; }
	.run-btn { background: #16a34a !important; border-color: #15803d !important; }
	.run-btn:hover { background: #15803d !important; }
	.filepath {
		padding: 4px 8px;
		border: 1px solid #475569;
		border-radius: 4px;
		background: #0f172a;
		color: white;
		font-size: 13px;
		width: 260px;
	}
	.spacer { flex: 1; }

	.load-error {
		background: #fee2e2;
		color: #991b1b;
		padding: 6px 12px;
		font-size: 13px;
	}

	/* Main 3-column layout */
	.main {
		display: flex;
		flex: 1;
		overflow: hidden;
	}

	.canvas-wrap {
		flex: 1;
		height: 100%;
		position: relative;
	}

	.canvas-wrap::after {
		content: '';
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		width: 3px;
		background: linear-gradient(to bottom, rgba(70, 120, 210, 0.7), rgba(70, 120, 210, 0.35));
		pointer-events: none;
		z-index: 14;
	}

	.props-flyout {
		position: absolute;
		right: 0;
		top: 12px;
		width: 300px;
		max-height: calc(100% - 24px);
		overflow: auto;
		z-index: 15;
		border: 1px solid #9eb8de;
		border-right: none;
		border-radius: 12px 0 0 12px;
		background: linear-gradient(180deg, #ffffff, #f8fbff);
		box-shadow: -10px 10px 30px rgba(20, 35, 60, 0.2);
		transition: width 160ms ease, max-height 160ms ease, box-shadow 180ms ease;
	}

	.props-flyout::before {
		content: '';
		position: absolute;
		left: -96px;
		top: 14px;
		width: 96px;
		height: 42px;
		background: linear-gradient(90deg, rgba(70, 120, 210, 0.14), rgba(70, 120, 210, 0.46));
		border-radius: 16px 0 0 16px;
		pointer-events: none;
		opacity: 0.62;
		transition: opacity 180ms ease;
	}

	.props-flyout.open::before {
		opacity: 1;
	}

	.props-flyout::after {
		content: '';
		position: absolute;
		left: -12px;
		top: 10px;
		width: 12px;
		height: 48px;
		background: rgba(70, 120, 210, 0.55);
		clip-path: polygon(100% 0, 0 50%, 100% 100%);
		pointer-events: none;
	}

	.flyout-tab {
		position: absolute;
		left: -94px;
		top: 10px;
		height: 30px;
		padding: 0 12px;
		display: inline-flex;
		align-items: center;
		font-size: 12px;
		font-weight: 700;
		color: #16385d;
		background: linear-gradient(180deg, #dcebff, #bfd8ff);
		border: 1px solid #8fb4e5;
		border-right: none;
		border-radius: 8px 0 0 8px;
		box-shadow: -3px 3px 10px rgba(30, 60, 100, 0.22);
		pointer-events: none;
		user-select: none;
	}

	.props-flyout:not(.open) {
		width: 260px;
		max-height: 56px;
		overflow: hidden;
		box-shadow: -6px 8px 16px rgba(20, 35, 60, 0.18);
	}

	/* Run modal */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0,0,0,0.45);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 100;
	}
	.modal {
		background: white;
		border-radius: 8px;
		padding: 20px;
		max-width: 800px;
		max-height: 80vh;
		width: 90%;
		overflow-y: auto;
	}
	.modal-header {
		display: flex;
		justify-content: space-between;
		font-weight: 700;
		font-size: 16px;
		margin-bottom: 12px;
	}
	.modal-header button {
		background: none;
		border: none;
		font-size: 18px;
		cursor: pointer;
	}
	.error { background: #fee2e2; padding: 10px; border-radius: 4px; font-size: 12px; white-space: pre-wrap; }
	.stdout { background: #f0fdf4; padding: 10px; border-radius: 4px; font-size: 12px; white-space: pre-wrap; }
	.plots { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
	.plots img { max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }
</style>
