<!--
  BlockNode.svelte
  A custom @xyflow/svelte node representing one bdsim block.
  Rendered inside the SvelteFlow canvas.
-->
<script lang="ts">
	import { Handle, Position, type Node, type NodeProps } from '@xyflow/svelte';
	import type { BlockData } from './types';

	// NodeProps<Node<BlockData>> gives us data typed as BlockData
	let { data } = $props() as NodeProps<Node<BlockData>>;

	const CLASS_COLOR: Record<string, string> = {
		function: '#d4e8ff',
		source:   '#d4ffd4',
		sink:     '#ffd4d4',
		transfer: '#ffe8b0',
		discrete: '#e8d4ff'
	};

	const bgColor = $derived(CLASS_COLOR[(data.blockClass as string)?.toLowerCase()] ?? '#eeeeee');
	const flipped = $derived(!!data.flipped);
	const inPos  = $derived(flipped ? Position.Right : Position.Left);
	const outPos = $derived(flipped ? Position.Left  : Position.Right);

	// Evenly space handles along the node height
	function handleTop(index: number, total: number): string {
		if (total === 1) return '50%';
		return `${(100 / (total + 1)) * (index + 1)}%`;
	}
</script>

<div class="block-node" style="background:{bgColor}">
	{#if data.url}
		<a class="doc-link" href={String(data.url)} target="_blank" rel="noreferrer" title="Documentation">↗</a>
	{/if}

	<!-- Input handles -->
	{#each Array(data.nin) as _, i}
		<Handle
			type="target"
			position={inPos}
			id={`in-${i}`}
			style="top:{handleTop(i, data.nin)}"
		/>
	{/each}

	<div class="block-type">{data.blockType}</div>
	<div class="block-label">{data.label}</div>

	{#if data.params?.length}
		<div class="params-tooltip">
			{#each data.params as [k, v]}
				<div>{k} = {JSON.stringify(v)}</div>
			{/each}
		</div>
	{/if}

	<!-- Output handles -->
	{#each Array(data.nout) as _, i}
		<Handle
			type="source"
			position={outPos}
			id={`out-${i}`}
			style="top:{handleTop(i, data.nout)}"
		/>
	{/each}
</div>

<style>
	.block-node {
		min-width: 110px;
		padding: 6px 14px;
		border: 1.5px solid #888;
		border-radius: 6px;
		font-size: 12px;
		text-align: center;
		cursor: pointer;
		position: relative;
		/* Let clicks pass through to xyflow's node wrapper so onnodeclick fires */
		pointer-events: none;
	}
	.doc-link {
		position: absolute;
		top: 3px;
		right: 5px;
		font-size: 10px;
		line-height: 1;
		color: #1d4ed8;
		text-decoration: none;
		background: rgba(255, 255, 255, 0.85);
		border-radius: 3px;
		padding: 1px 2px;
		pointer-events: all;
	}
	.doc-link:hover {
		color: #1e40af;
	}
	/* Re-enable pointer events on handles so wiring still works */
	:global(.svelte-flow__handle) {
		pointer-events: all !important;
	}

	/* Selected node highlight */
	:global(.svelte-flow__node.selected) .block-node {
		border-color: #2563eb;
		box-shadow: 0 0 0 2px #93c5fd;
	}

	/* Target (input) handles — triangle pointing INTO the block from whichever side */
	:global(.svelte-flow__handle.target.svelte-flow__handle-left) {
		width: 8px; height: 8px;
		border-radius: 0; border: none;
		background: #111;
		clip-path: polygon(0 0, 100% 50%, 0 100%); /* → */
		transform: translateY(-50%);
	}
	:global(.svelte-flow__handle.target.svelte-flow__handle-right) {
		width: 8px; height: 8px;
		border-radius: 0; border: none;
		background: #111;
		clip-path: polygon(100% 0, 0 50%, 100% 100%); /* ← */
		transform: translateY(-50%);
	}
	:global(.svelte-flow__handle.target:hover),
	:global(.svelte-flow__handle.target.connectingfrom) {
		background: #2563eb;
	}
	.block-type {
		font-weight: 700;
		font-size: 13px;
		letter-spacing: 0.03em;
	}
	.block-label {
		color: #444;
		font-size: 11px;
		margin-top: 1px;
	}
	/* Hover tooltip showing params */
	.params-tooltip {
		position: absolute;
		top: calc(100% + 6px);
		left: 50%;
		transform: translateX(-50%);
		background: #1e293b;
		color: #e2e8f0;
		padding: 6px 10px;
		border-radius: 6px;
		font-size: 11px;
		white-space: nowrap;
		pointer-events: none;
		opacity: 0;
		z-index: 100;
		box-shadow: 0 2px 8px rgba(0,0,0,0.4);
		transition: opacity 120ms;
		text-align: left;
		line-height: 1.6;
	}
	:global(.svelte-flow__node:hover) { z-index: 1000 !important; }
	:global(.svelte-flow__node:hover) .params-tooltip { opacity: 1; }
</style>
