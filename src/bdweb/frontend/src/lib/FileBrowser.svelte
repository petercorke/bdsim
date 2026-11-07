<!-- FileBrowser.svelte — server-side filesystem browser rooted at ~.
     Emits onselect(absPath) when a .bd file is chosen, oncancel on dismiss. -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from './api';

	let { onselect, oncancel }: {
		onselect: (path: string) => void;
		oncancel: () => void;
	} = $props();

	type Entry = { name: string; type: 'dir' | 'file'; abs?: string };

	let dir = $state('');        // relative to ~
	let absDir = $state('');     // absolute path of current dir (for display)
	let entries: Entry[] = $state([]);
	let loading = $state(false);
	let error = $state('');

	const LS_KEY = 'bdweb:lastBrowseDir';

	async function navigate(relDir: string, save = true) {
		loading = true;
		error = '';
		try {
			const res = await api.ls(relDir);
			dir = res.dir;
			absDir = res.abs;
			entries = res.entries;
			if (save) localStorage.setItem(LS_KEY, res.dir);
		} catch (e) {
			error = String(e);
		} finally {
			loading = false;
		}
	}

	function up() {
		// Go up one level (but not above ~)
		if (!dir) return;
		const parts = dir.split('/');
		parts.pop();
		navigate(parts.join('/'));
	}

	function pickFile(entry: Entry) {
		if (entry.abs) onselect(entry.abs);
	}

	// Breadcrumb: split the relative dir into clickable segments
	function crumbs(): { label: string; rel: string }[] {
		const result: { label: string; rel: string }[] = [{ label: '~', rel: '' }];
		if (!dir) return result;
		const parts = dir.split('/');
		parts.forEach((part, i) => {
			result.push({ label: part, rel: parts.slice(0, i + 1).join('/') });
		});
		return result;
	}

	onMount(() => {
		const last = localStorage.getItem('bdweb:lastBrowseDir') ?? '';
		navigate(last);
	});
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="overlay" role="dialog" aria-modal="true">
	<div class="browser">
		<header class="browser-header">
			<span class="title">Open diagram</span>
			<button class="close-btn" onclick={oncancel}>✕</button>
		</header>

		<nav class="breadcrumb">
			{#each crumbs() as crumb, i}
				{#if i > 0}<span class="sep">/</span>{/if}
				<button class="crumb" onclick={() => navigate(crumb.rel)}>{crumb.label}</button>
			{/each}
		</nav>

		<div class="file-list">
			{#if loading}
				<div class="status">Loading…</div>
			{:else if error}
				<div class="status error">{error}</div>
			{:else}
				{#if dir}
					<button class="entry dir" onclick={up}>
						<span class="icon">📁</span>..
					</button>
				{/if}
				{#each entries as entry}
					{#if entry.type === 'dir'}
						<button class="entry dir" onclick={() => navigate(dir ? dir + '/' + entry.name : entry.name)}>
							<span class="icon">📁</span>{entry.name}
						</button>
					{:else}
						<button class="entry file" onclick={() => pickFile(entry)}>
							<span class="icon">📄</span>{entry.name}
						</button>
					{/if}
				{/each}
				{#if entries.length === 0}
					<div class="status muted">No .bd files or subdirectories here.</div>
				{/if}
			{/if}
		</div>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.45);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.browser {
		background: #1e1e2e;
		border: 1px solid #444;
		border-radius: 8px;
		width: 520px;
		max-height: 70vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
	}

	.browser-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 14px;
		border-bottom: 1px solid #333;
		background: #181825;
	}

	.title {
		font-weight: 600;
		font-size: 0.9rem;
		color: #cdd6f4;
	}

	.close-btn {
		background: none;
		border: none;
		color: #888;
		cursor: pointer;
		font-size: 1rem;
		padding: 2px 6px;
	}
	.close-btn:hover { color: #cdd6f4; }

	.breadcrumb {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 2px;
		padding: 6px 14px;
		border-bottom: 1px solid #2a2a3d;
		background: #1a1a2e;
		font-size: 0.8rem;
	}

	.crumb {
		background: none;
		border: none;
		color: #89b4fa;
		cursor: pointer;
		padding: 1px 3px;
		border-radius: 3px;
	}
	.crumb:hover { background: #2a2a3d; }

	.sep { color: #555; }

	.file-list {
		overflow-y: auto;
		flex: 1;
		padding: 6px 0;
	}

	.entry {
		display: flex;
		align-items: center;
		gap: 8px;
		width: 100%;
		text-align: left;
		background: none;
		border: none;
		color: #cdd6f4;
		padding: 6px 16px;
		cursor: pointer;
		font-size: 0.85rem;
		border-radius: 0;
	}
	.entry:hover { background: #2a2a3d; }
	.entry.file { color: #a6e3a1; }

	.icon { font-size: 1rem; width: 1.4em; flex-shrink: 0; }

	.status {
		padding: 20px 16px;
		color: #888;
		font-size: 0.85rem;
	}
	.status.error { color: #f38ba8; }
	.status.muted { color: #555; }
</style>
