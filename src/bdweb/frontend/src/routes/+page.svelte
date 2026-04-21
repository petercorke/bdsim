<script lang="ts">
	import { onMount, tick } from 'svelte';
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
	import FlowRef from '$lib/FlowRef.svelte';
	import FileBrowser from '$lib/FileBrowser.svelte';
	import ContextMenu from '$lib/ContextMenu.svelte';
	import PropsCard from '$lib/PropsCard.svelte';

	// ── Custom node type registry ───────────────────────────────────────────
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const nodeTypes: NodeTypes = { bdsimBlock: BlockNode as any };

	// fitView / updateNodeInternals are set by FlowRef once SvelteFlow mounts (needs its context)
	let fitView: (opts?: { padding?: number }) => void = () => {};
	let updateNodeInternals: ((ids: string | string[]) => void) | null = $state(null);

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
	let runResult: { stdout: string; stderr: string; returncode: number } | null = $state(null);
	let running = $state(false);

	// File browser modal
	let showBrowser = $state(false);

	// Context menu
	let ctxMenu: { x: number; y: number } | null = $state(null);

	// Canvas wrapper ref for props card positioning
	let canvasEl: HTMLElement | null = $state(null);

	// Props card position — computed from selected node + viewport transform
	const propCardPos = $derived(
		(() => {
			if (!selectedNodeId || !canvasEl) return null;
			const node = nodes.find((n) => n.id === selectedNodeId);
			if (!node) return null;
			const rect = canvasEl.getBoundingClientRect();
			const sx = rect.left + node.position.x * viewport.zoom + viewport.x;
			const sy = rect.top  + node.position.y * viewport.zoom + viewport.y;
			const nodeW = 130 * viewport.zoom;
			const nodeH =  58 * viewport.zoom;
			const CARD_W = 290;
			let cardX = sx + nodeW + 12;
			if (cardX + CARD_W > window.innerWidth - 10) cardX = sx - CARD_W - 12;
			return { x: Math.max(10, cardX), y: Math.max(50, sy + nodeH / 2 - 80) };
		})()
	);

	// File path for load/save (full absolute path, set by browser or ?load= param)
	let filePath = $state('');
	// Display label — just the filename without the directory
	const fileLabel = $derived(filePath ? filePath.split('/').pop()! : '');

	// Incrementing counter for unique node IDs
	let nodeCounter = $state(0);

	// ── Load block library on mount; auto-load ?load=path if present ───────
	onMount(async () => {
		try {
			library = await api.blocks();
		} catch (e) {
			loadError = String(e);
			return; // no point auto-loading if we can't reach the backend
		}
		// Auto-load a file passed via ?load=<path> (set by `bdweb myfile.bd`)
		const autoPath = new URLSearchParams(window.location.search).get('load');
		if (autoPath) {
			filePath = autoPath;
			await handleLoad();
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
			flipped: !!(n.data.flipped),
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
					flipped: !!b.flipped,
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
		ctxMenu = null;
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

	function onNodeContextMenu({ node, event }: { node: Node<BlockData>; event: MouseEvent }) {
		event.preventDefault();
		// Ensure the right-clicked node is selected
		if (!node.selected) {
			nodes = nodes.map((n) => ({ ...n, selected: n.id === node.id }));
		}
		ctxMenu = { x: event.clientX, y: event.clientY };
	}

	function flipSelected() {
		const flippedIds: string[] = [];
		nodes = nodes.map((n) => {
			if (!n.selected) return n;
			flippedIds.push(n.id);
			return { ...n, data: { ...n.data, flipped: !n.data.flipped } };
		});
		// Tell xyflow to re-measure handles so edges follow the new positions
		tick().then(() => updateNodeInternals?.(flippedIds));
	}

	function deleteSelected() {
		const selectedIds = new Set(nodes.filter((n) => n.selected).map((n) => n.id));
		if (!selectedIds.size) return;
		nodes = nodes.filter((n) => !n.selected);
		edges = edges.filter((e) => !selectedIds.has(e.source) && !selectedIds.has(e.target));
		if (selectedNodeId && selectedIds.has(selectedNodeId)) onPaneClick();
	}

	function onWindowKeydown(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
		if (e.key === 'f' || e.key === 'F') { flipSelected(); return; }
		if (e.key === 'Delete' || e.key === 'Backspace') { deleteSelected(); return; }
	}

	// ── Toolbar actions ────────────────────────────────────────────────────
	async function handleBrowse() {
		showBrowser = true;
	}

	async function onBrowserSelect(path: string) {
		showBrowser = false;
		filePath = path;
		await handleLoad();
	}

	async function handleLoad() {
		const path = filePath.trim();
		if (!path) return;
		try {
			const diagram = await api.load(path);
			fromDiagram(diagram);
			selectedNodeId = null;
			await tick();
			fitView({ padding: 0.12 });
		} catch (e) {
			alert('Load failed: ' + e);
		}
	}

	async function handleSave() {
		const path = filePath.trim();
		if (!path) { alert('Select a file via Browse first.'); return; }
		try {
			const { exists } = await api.exists(path);
			if (exists && !confirm(`Overwrite ${path.split('/').pop()}?`)) return;
			await api.save(path, toDiagram());
		} catch (e) {
			alert('Save failed: ' + e);
		}
	}

	async function handleRun() {
		const path = filePath.trim();
		if (!path) { alert('Save the file via Browse + Save before running.'); return; }
		running = true;
		runResult = null;
		try {
			// Save first so bdrun sees the latest diagram
			await api.save(path, toDiagram());
			runResult = await api.run(path);
		} catch (e) {
			runResult = { stdout: '', stderr: String(e), returncode: -1 };
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
<svelte:window onkeydown={onWindowKeydown} />
<!-- ── Layout ─────────────────────────────────────────────────────────── -->
<div class="app">
	<!-- Toolbar -->
	<header class="toolbar">
		<span class="logo">bdweb</span>

		<button onclick={handleNew}>New</button>

		<span class="filepath" title={filePath}>{fileLabel || 'no file'}</span>
		<button onclick={handleBrowse}>Browse…</button>
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
		<div class="canvas-wrap" role="region" ondrop={onDrop} ondragover={onDragOver} bind:this={canvasEl}>
			<SvelteFlow
				bind:nodes
				bind:edges
				bind:viewport
				{nodeTypes}
				snapGrid={[10, 10]}
				defaultEdgeOptions={{ type: 'smoothstep' }}
				panOnDrag={false}
				selectionOnDrag={true}
				panActivationKeyCode="Alt"
				panOnScroll={true}
				zoomOnScroll={false}
				zoomActivationKeyCode="Alt"
				multiSelectionKeyCode="Meta"
				deleteKeyCode={null}
				onnodeclick={onNodeClick}
				onnodecontextmenu={onNodeContextMenu}
				onpaneclick={onPaneClick}
			>
				<FlowRef onready={(flow, uni) => { fitView = flow.fitView; updateNodeInternals = uni; }} />
				<Controls />
				<Background variant={BackgroundVariant.Dots} gap={20} />
				<MiniMap />
			</SvelteFlow>
		</div>
	</div>
</div>

<!-- Floating properties card -->
{#if propCardPos && selectedBlockType}
	<PropsCard
		x={propCardPos.x}
		y={propCardPos.y}
		blockType={selectedBlockType}
		blockName={selectedBlockName}
		params={selectedParams}
		blockInfo={selectedBlockInfo}
		onnameupdate={onNameUpdate}
		onupdate={onParamUpdate}
		onapplied={onPropsApplied}
		onclose={onPaneClick}
	/>
{/if}

<!-- Context menu -->
{#if ctxMenu}
	<ContextMenu
		x={ctxMenu.x}
		y={ctxMenu.y}
		onflip={flipSelected}
		ondelete={deleteSelected}
		onclose={() => { ctxMenu = null; }}
	/>
{/if}

<!-- File browser modal -->
{#if showBrowser}
	<FileBrowser onselect={onBrowserSelect} oncancel={() => { showBrowser = false; }} />
{/if}

<!-- Run results modal -->
{#if runResult}
	<div class="modal-backdrop" role="dialog" aria-modal="true">
		<div class="modal">
			<div class="modal-header">
				Run Output {#if runResult.returncode !== 0}<span class="exit-code">(exit {runResult.returncode})</span>{/if}
				<button onclick={() => (runResult = null)}>✕</button>
			</div>

			{#if runResult.stdout}
				<pre class="stdout">{runResult.stdout}</pre>
			{/if}

			{#if runResult.stderr}
				<pre class="error">{runResult.stderr}</pre>
			{/if}

			{#if !runResult.stdout && !runResult.stderr}
				<p class="no-output">(no output)</p>
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
		color: #94a3b8;
		font-size: 13px;
		max-width: 200px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		cursor: default;
		user-select: none;
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
	.exit-code { font-weight: 400; color: #dc2626; margin-left: 8px; }
	.no-output { color: #6b7280; font-style: italic; margin: 8px 0; }
</style>
