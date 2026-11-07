<!-- ContextMenu.svelte — right-click menu for block nodes -->
<script lang="ts">
	let { x, y, onflip, ondelete, onclose }: {
		x: number;
		y: number;
		onflip: () => void;
		ondelete: () => void;
		onclose: () => void;
	} = $props();
</script>

<svelte:window onpointerdown={onclose} onkeydown={(e) => e.key === 'Escape' && onclose()} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div class="ctx-menu" style="left:{x}px; top:{y}px" onpointerdown={(e) => e.stopPropagation()}>
	<button onclick={() => { onflip(); onclose(); }}>
		Flip <kbd>F</kbd>
	</button>
	<hr />
	<button class="danger" onclick={() => { ondelete(); onclose(); }}>
		Delete <kbd>⌫</kbd>
	</button>
</div>

<style>
	.ctx-menu {
		position: fixed;
		z-index: 1000;
		background: #1e293b;
		border: 1px solid #334155;
		border-radius: 6px;
		padding: 4px 0;
		min-width: 140px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
	}
	button {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		padding: 6px 14px;
		background: none;
		border: none;
		color: #e2e8f0;
		font-size: 13px;
		text-align: left;
		cursor: pointer;
		gap: 16px;
	}
	button:hover { background: #334155; }
	button.danger { color: #f87171; }
	button.danger:hover { background: #3f1515; }
	hr { border: none; border-top: 1px solid #334155; margin: 3px 0; }
	kbd {
		font-size: 11px;
		background: #0f172a;
		border: 1px solid #475569;
		border-radius: 3px;
		padding: 1px 5px;
		color: #94a3b8;
	}
</style>
