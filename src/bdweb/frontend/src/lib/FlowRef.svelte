<!-- FlowRef.svelte — must be rendered as a child of <SvelteFlow>.
     Calls useSvelteFlow() (which requires the SvelteFlow context) and
     exposes the instance to the parent via the onready callback. -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { useSvelteFlow, useUpdateNodeInternals } from '@xyflow/svelte';

	let { onready }: { onready: (flow: ReturnType<typeof useSvelteFlow>, updateNodeInternals: (ids: string | string[]) => void) => void } = $props();

	const flow = useSvelteFlow();
	const updateNodeInternals = useUpdateNodeInternals();

	onMount(() => onready(flow, updateNodeInternals));
</script>
