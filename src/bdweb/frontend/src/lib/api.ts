// Thin wrapper around fetch for all /api calls.
import type { BlockInfo, BlockLibrary, Diagram } from './types';

const BASE = '/api';

async function json<T>(url: string, init?: RequestInit): Promise<T> {
	const res = await fetch(BASE + url, init);
	if (!res.ok) {
		const text = await res.text().catch(() => res.statusText);
		throw new Error(`API ${url}: ${res.status} ${text}`);
	}
	return res.json() as Promise<T>;
}

export const api = {
	/** Return block library grouped by blockclass. */
	blocks(): Promise<BlockLibrary> {
		return json('/blocks');
	},

	/** Return metadata for one block type. */
	blockInfo(name: string): Promise<BlockInfo> {
		return json(`/blockinfo/${encodeURIComponent(name)}`);
	},

	/** List directories and .bd files under ~ (dir is relative to ~). */
	ls(dir = ""): Promise<{ dir: string; abs: string; entries: { name: string; type: "dir" | "file"; abs?: string }[] }> {
		return json(`/ls?dir=${encodeURIComponent(dir)}`);
	},

	/** Check whether a path exists on the server filesystem. */
	exists(path: string): Promise<{ exists: boolean }> {
		return json(`/exists?path=${encodeURIComponent(path)}`);
	},

	/** Load a .bd file from a filesystem path (server-side). */
	load(path: string): Promise<Diagram> {
		return json('/load', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ path })
		});
	},

	/** Save the current diagram to a filesystem path (server-side). */
	save(path: string, diagram: Diagram): Promise<{ saved: string }> {
		return json('/save', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ path, diagram })
		});
	},

	/** Save the diagram, then run bdrun; returns stdout, stderr, and returncode. */
	run(path: string): Promise<{ stdout: string; stderr: string; returncode: number }> {
		return json('/run', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ path })
		});
	}
};
