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

	<!-- Input handles (left side) -->
	{#each Array(data.nin) as _, i}
		<Handle
			type="target"
			position={Position.Left}
			id={`in-${i}`}
			style="top:{handleTop(i, data.nin)}"
		/>
	{/each}

	<div class="block-type">{data.blockType}</div>
	<div class="block-label">{data.label}</div>

	<!-- Show param summary if any -->
	{#if data.params?.length}
		<div class="block-params">
			{#each data.params.slice(0, 3) as [k, v]}
				<span>{k}={JSON.stringify(v)}</span>
			{/each}
			{#if data.params.length > 3}
				<span class="more">+{data.params.length - 3} more</span>
			{/if}
		</div>
	{/if}

	<!-- Output handles (right side) -->
	{#each Array(data.nout) as _, i}
		<Handle
			type="source"
			position={Position.Right}
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
	.block-params {
		margin-top: 4px;
		display: flex;
		flex-direction: column;
		gap: 1px;
		font-size: 10px;
		color: #555;
	}
	.more {
		color: #888;
		font-style: italic;
	}
</style>
