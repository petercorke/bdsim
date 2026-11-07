<!--
  Palette.svelte
  Left sidebar showing the block library grouped by category.
  Dragging a block item onto the canvas triggers a dragstart with the block
  type in the dataTransfer payload.
-->
<script lang="ts">
	import type { BlockLibrary } from '$lib/types';

	let { library = {} as BlockLibrary }: { library?: BlockLibrary } = $props();

	// Which categories are expanded
	let open: Record<string, boolean> = $state({});
	const hasOpenSections = $derived(Object.values(open).some(Boolean));

	// Colour per blockclass (matches bdedit convention)
	const CLASS_COLOR: Record<string, string> = {
		Function: '#d4e8ff',
		Source:   '#d4ffd4',
		Sink:     '#ffd4d4',
		Transfer: '#ffe8b0',
		Discrete: '#e8d4ff',
		Other:    '#eeeeee'
	};

	function color(cls: string) {
		return CLASS_COLOR[cls] ?? CLASS_COLOR['Other'];
	}

	function onDragStart(event: DragEvent, blockName: string) {
		event.dataTransfer!.setData('application/bdsim-block', blockName);
		event.dataTransfer!.effectAllowed = 'copy';
	}

	function collapseAll() {
		open = {};
	}

	const CATEGORY_ORDER = ['Source','Function','Transfer','Clocked','Subsystem','Graphics','Sink'];

	// Maps package name → short badge label. Extend for new toolboxes.
	const PACKAGE_LABEL: Record<string, string> = {
		roboticstoolbox:      'robotics',
		machinevisiontoolbox: 'vision',
		spatialmathstoolbox:  'spatial',
	};

	// Derive the set of non-bdsim packages present in the library
	const extraPackages = $derived(
		[...new Set(
			Object.values(library).flat()
				.map(b => b.package)
				.filter(p => p && p !== 'bdsim')
		)].sort()
	);

	// Filter state: pkg → visible (default true)
	let pkgVisible: Record<string, boolean> = $state({});

	function isPkgVisible(pkg: string) {
		// bdsim blocks always shown; extras follow checkbox
		if (!pkg || pkg === 'bdsim') return true;
		return pkgVisible[pkg] !== false; // default on
	}

	// Sort categories by desired order; unknowns go to end alphabetically
	const sortedCategories = $derived(
		Object.entries(library)
			.sort(([a], [b]) => {
				const ia = CATEGORY_ORDER.indexOf(a);
				const ib = CATEGORY_ORDER.indexOf(b);
				if (ia === -1 && ib === -1) return a.localeCompare(b);
				if (ia === -1) return 1;
				if (ib === -1) return -1;
				return ia - ib;
			})
			.map(([cls, blocks]) => [
				cls,
				[...blocks]
					.filter(b => isPkgVisible(b.package))
					.sort((a, b) => a.name.localeCompare(b.name))
			] as [string, typeof blocks])
			.filter(([, blocks]) => blocks.length > 0)
	);
</script>

<aside class="palette">
	<div class="logo-wrap">
		<img src="/bdsim_logo.png" alt="bdsim" class="logo-img" />
	</div>

	{#if extraPackages.length > 0}
		<div class="pkg-filters">
			<div class="pkg-filters-title">Package filter</div>
			{#each extraPackages as pkg}
				{@const label = PACKAGE_LABEL[pkg] ?? pkg}
				<label class="pkg-filter-row">
					<input
						type="checkbox"
						checked={pkgVisible[pkg] !== false}
						onchange={() => (pkgVisible[pkg] = pkgVisible[pkg] === false ? true : false)}
					/>
					<span class="pkg-badge pill">{label}</span>
				</label>
			{/each}
		</div>
	{/if}

	<div class="menu-tools" class:connected={hasOpenSections}>
		<button
			class="collapse-btn"
			class:connected={hasOpenSections}
			type="button"
			onclick={collapseAll}
			disabled={!hasOpenSections}
		>
			Collapse all
		</button>
	</div>

	{#each sortedCategories as [cls, blocks]}
		<div class="category">
			<!-- svelte-ignore a11y_click_events_have_key_events -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div class="category-header" style="background:{color(cls)}" onclick={() => (open[cls] = !open[cls])}>
				<span class="chevron">{open[cls] ? '▾' : '▸'}</span>
				{cls}
				<span class="count">{blocks.length}</span>
			</div>

			{#if open[cls]}
				<ul>
					{#each blocks as block}
						{@const badge = PACKAGE_LABEL[block.package]}
						<li
							draggable="true"
							ondragstart={(e) => onDragStart(e, block.name)}
							title="{block.classname} ({block.package}) — {block.nin} in / {block.nout} out"
						>
							{block.name}
							{#if badge}<span class="pkg-badge">{badge}</span>{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/each}
</aside>

<style>
	.palette {
		width: 210px;
		min-width: 210px;
		overflow-y: auto;
		background: #fafafa;
		border-right: 1px solid #ddd;
		font-size: 13px;
		user-select: none;
	}
	.logo-wrap {
		width: 100%;
		background: #fff;
		border-bottom: 2px solid #6aaa3a;
		box-sizing: border-box;
		padding: 0;
	}
	.logo-img {
		width: 100%;
		display: block;
		object-fit: contain;
	}
	.pkg-filters {
		padding: 6px 10px;
		border-bottom: 1px solid #ddd;
		background: #f7f7f7;
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	.pkg-filters-title {
		font-size: 12px;
		font-weight: 600;
		color: #333;
		margin-bottom: 2px;
	}
	.pkg-filter-row {
		display: flex;
		align-items: center;
		gap: 6px;
		cursor: pointer;
		font-size: 12px;
	}
	.menu-tools {
		padding: 6px 10px 4px;
		border-bottom: 1px solid #ddd;
		background: #f7f7f7;
		position: relative;
		display: flex;
		justify-content: center;
	}
	.collapse-btn {
		width: auto;
		min-width: 0;
		border: 1px solid #c9d1d9;
		background: #fff;
		border-radius: 8px;
		padding: 5px 16px;
		font-size: 12px;
		cursor: pointer;
		position: relative;
	}
	.collapse-btn:hover {
		background: #eef2f6;
	}
	.collapse-btn:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.collapse-btn.connected::after {
		content: '';
		position: absolute;
		left: 50%;
		bottom: -8px;
		transform: translateX(-50%);
		width: 0;
		height: 0;
		border-left: 7px solid transparent;
		border-right: 7px solid transparent;
		border-top: 7px solid #b7c5d8;
		pointer-events: none;
	}
	.menu-tools::after {
		content: none;
	}
	.category-header {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 5px 10px;
		cursor: pointer;
		font-weight: 600;
		border-bottom: 1px solid #e0e0e0;
	}
	.category-header:hover { filter: brightness(0.95); }
	.chevron { font-size: 15px; width: 18px; line-height: 1; }
	.count {
		margin-left: auto;
		background: rgba(0,0,0,0.12);
		border-radius: 8px;
		padding: 0 5px;
		font-size: 11px;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	li {
		padding: 4px 10px 4px 22px;
		cursor: grab;
		border-bottom: 1px solid #f0f0f0;
	}
	li:hover { background: #e8f0fe; }
	li:active { cursor: grabbing; }
	.pkg-badge {
		margin-left: 5px;
		font-size: 9px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		vertical-align: middle;
	}
	.pkg-badge.pill {
		display: inline-block;
		background: #cc2200;
		color: #fff;
		border-radius: 999px;
		padding: 1px 7px;
		margin-left: 0;
	}
	/* inline badge in block list rows — pill style too */
	li .pkg-badge {
		background: #cc2200;
		color: #fff;
		border-radius: 999px;
		padding: 1px 6px;
	}
</style>
