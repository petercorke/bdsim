<!--
  PropsPanel.svelte
  Right-side panel showing editable parameters for the selected node.
  Emits `update` with new params array when user changes a value.
-->
<script lang="ts">
	import type { BlockInfo } from '$lib/types';

	interface Props {
		blockType?: string;
		blockName?: string;
		params?: [string, unknown][];
		blockInfo?: BlockInfo | null;
		onnameupdate?: (name: string) => void;
		onupdate?: (params: [string, unknown][]) => void;
		onapplied?: () => void;
	}

	let {
		blockType = '',
		blockName = '',
		params = [],
		blockInfo = null,
		onnameupdate,
		onupdate,
		onapplied
	}: Props = $props();

	let localName = $state('');
	$effect(() => {
		localName = blockName;
	});

	// Local mutable copy — reset when selection changes.
	// If the node has no stored params yet, seed from blockInfo's param defaults.
	let local: [string, unknown][] = $state([]);
	$effect(() => {
		if (params.length > 0) {
			local = params.map(([k, v]) => [k, v] as [string, unknown]);
		} else if (blockInfo?.params) {
			local = Object.entries(blockInfo.params)
				.map(([k, p]) => [k, p.default] as [string, unknown]);
		} else {
			local = [];
		}
	});

	function set(index: number, value: unknown) {
		local[index] = [local[index][0], value];
	}

	function submit() {
		onnameupdate?.(localName);
		onupdate?.(local.map(([k, v]) => [k, v] as [string, unknown]));
		onapplied?.();
	}

	function onFormKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === 'NumpadEnter') {
			e.preventDefault();
			submit();
		}
	}

	function paramType(name: string): 'bool' | 'number' | 'str' | 'list' {
		return blockInfo?.params?.[name]?.type ?? 'str';
	}

	function inputType(t: string): 'checkbox' | 'number' | 'text' {
		if (t === 'bool') return 'checkbox';
		if (t === 'number') return 'number';
		return 'text'; // 'str' and 'list' both use text (list as JSON)
	}
</script>

<aside class="props-panel">
	{#if blockType}
		<div class="panel-header">
			{blockType}
			{#if blockInfo?.url}
				<a href={blockInfo.url} target="_blank" rel="noreferrer" title="Documentation">↗</a>
			{/if}
		</div>

		{#if local.length === 0}
			<form onsubmit={(e) => { e.preventDefault(); submit(); }} onkeydown={onFormKeydown}>
				<div class="field">
					<label for="block-name">name</label>
					<input
						id="block-name"
						type="text"
						value={localName}
						oninput={(e) => (localName = (e.target as HTMLInputElement).value)}
					/>
				</div>
				<p class="empty">No parameters</p>
				<button type="button" onclick={submit}>Apply</button>
			</form>
		{:else}
			<form onsubmit={(e) => { e.preventDefault(); submit(); }} onkeydown={onFormKeydown}>
				<div class="field">
					<label for="block-name">name</label>
					<input
						id="block-name"
						type="text"
						value={localName}
						oninput={(e) => (localName = (e.target as HTMLInputElement).value)}
					/>
				</div>
				{#each local as [name, value], i}
					<div class="field">
						<label for="p-{i}" title={paramType(name)}>
							{name}
							{#if paramType(name) === 'list'}
								<span class="hint" title="JSON list">[ ]</span>
							{/if}
						</label>

						{#if inputType(paramType(name)) === 'checkbox'}
							<input
								id="p-{i}"
								type="checkbox"
								checked={!!value}
								onchange={(e) => set(i, (e.target as HTMLInputElement).checked)}
							/>
						{:else if inputType(paramType(name)) === 'number'}
							<input
								id="p-{i}"
								type="number"
								step="any"
								placeholder={value === null ? 'None' : ''}
								value={value === null ? '' : value}
								oninput={(e) => {
									const raw = (e.target as HTMLInputElement).value;
									if (raw === '') { set(i, null); return; }
									const n = parseFloat(raw);
									set(i, isNaN(n) ? value : n);
								}}
							/>
						{:else}
							<input
								id="p-{i}"
								type="text"
								placeholder={value === null ? 'None' : ''}
								value={value === null ? '' : typeof value === 'string' ? value : JSON.stringify(value)}
								oninput={(e) => {
									const raw = (e.target as HTMLInputElement).value;
									if (raw === '') { set(i, null); return; }
									try { set(i, JSON.parse(raw)); } catch { set(i, raw); }
								}}
							/>
						{/if}
					</div>
				{/each}

				<button type="button" onclick={submit}>Apply</button>
			</form>
		{/if}
	{:else}
		<p class="empty">Click a block to edit its properties.</p>
	{/if}
</aside>

<style>
	.props-panel {
		width: 100%;
		min-width: 0;
		overflow-y: auto;
		background: #fff;
		border-left: none;
		font-size: 13px;
	}
	.panel-header {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 12px;
		font-weight: 700;
		font-size: 14px;
		border-bottom: 1px solid #ddd;
		background: #f0f0f0;
	}
	.panel-header a { color: #2563eb; font-size: 12px; }
	.empty { padding: 12px; color: #888; font-size: 12px; }
	form { padding: 8px 10px; display: flex; flex-direction: column; gap: 8px; }
	.field { display: flex; flex-direction: column; gap: 2px; }
	label {
		font-weight: 600;
		color: #333;
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.hint {
		display: inline-block;
		width: 14px;
		height: 14px;
		background: #bbb;
		border-radius: 50%;
		text-align: center;
		line-height: 14px;
		font-size: 9px;
		color: white;
		cursor: help;
	}
	input[type='text'], input[type='number'] {
		border: 1px solid #ccc;
		border-radius: 4px;
		padding: 3px 6px;
		font-size: 12px;
		width: 100%;
		box-sizing: border-box;
	}
	button {
		background: #2563eb;
		color: white;
		border: none;
		border-radius: 4px;
		padding: 5px 10px;
		cursor: pointer;
		font-size: 12px;
		align-self: flex-start;
	}
	button:hover { background: #1d4ed8; }
</style>
