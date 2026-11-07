<!-- PropsCard.svelte — floating properties panel anchored near the selected block. -->
<script lang="ts">
	import PropsPanel from './PropsPanel.svelte';
	import type { BlockInfo } from './types';

	let {
		x, y,
		blockType = '',
		blockName = '',
		params = [],
		blockInfo = null,
		onnameupdate,
		onupdate,
		onapplied,
		onclose
	}: {
		x: number;
		y: number;
		blockType?: string;
		blockName?: string;
		params?: [string, unknown][];
		blockInfo?: BlockInfo | null;
		onnameupdate?: (name: string) => void;
		onupdate?: (params: [string, unknown][]) => void;
		onapplied?: () => void;
		onclose?: () => void;
	} = $props();
</script>

<div class="card" style="left:{x}px; top:{y}px">
	<button class="close-btn" onclick={onclose}>✕</button>
	<PropsPanel
		{blockType}
		{blockName}
		{params}
		{blockInfo}
		{onnameupdate}
		{onupdate}
		{onapplied}
	/>
</div>

<style>
	.card {
		position: fixed;
		z-index: 20;
		width: 280px;
		max-height: 60vh;
		overflow-y: auto;
		background: white;
		border: 1px solid #9eb8de;
		border-radius: 8px;
		box-shadow: 0 4px 24px rgba(20, 35, 60, 0.25);
	}
	.close-btn {
		position: absolute;
		top: 6px;
		right: 8px;
		background: none;
		border: none;
		font-size: 14px;
		color: #888;
		cursor: pointer;
		line-height: 1;
		padding: 2px 4px;
		border-radius: 3px;
		z-index: 1;
	}
	.close-btn:hover { background: #eee; color: #333; }
</style>
