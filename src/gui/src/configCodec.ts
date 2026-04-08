import yaml from 'js-yaml';
import { Edge, Node } from 'reactflow';
import { ConfigAsset, ConfigPipe, Medium } from './types';

type AnyRecord = Record<string, unknown>;

function normalizeMedium(raw: unknown): Medium {
  const value = String(raw ?? '').trim().toLowerCase();
  if (value === 'data') return 'data';
  if (value === 'electric' || value === 'thermal' || value === 'monetary') return value as Medium;
  return 'electric';
}

function isPipeNode(node: Node): boolean {
  const data = (node.data ?? {}) as AnyRecord;
  return String(data.kind ?? 'asset') === 'pipe';
}

function handleIndex(handle: string, prefix: 'in_' | 'out_'): number | null {
  if (!handle.startsWith(prefix)) return null;
  const suffix = Number(handle.slice(prefix.length));
  if (!Number.isFinite(suffix) || suffix < 1) return null;
  return Math.floor(suffix);
}

function normalizeGroups(raw: unknown): string[][] {
  if (raw === null || raw === undefined) return [];

  if (typeof raw === 'string') {
    return [[raw]];
  }

  if (!Array.isArray(raw)) {
    return [];
  }

  if (raw.every((item) => typeof item === 'string')) {
    return [raw.map((item) => String(item))];
  }

  const groups: string[][] = [];
  for (const item of raw) {
    if (typeof item === 'string') {
      groups.push([item]);
      continue;
    }
    if (!Array.isArray(item)) continue;

    const group: string[] = [];
    for (const entry of item) {
      if (typeof entry !== 'string') continue;
      group.push(entry);
    }

    if (group.length > 0) {
      groups.push(group);
    }
  }

  return groups;
}

function toSortedGroups(groupMap: Map<number, string[]>): string[][] {
  return Array.from(groupMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, refs]) => refs);
}

export function nodesToAssets(nodes: Node[]): ConfigAsset[] {
  return nodes
    .filter((node) => !isPipeNode(node))
    .map((node) => {
      const data = (node.data ?? {}) as AnyRecord;
      const params = ((data.params ?? {}) as ConfigAsset['params']) ?? {};
      return {
        id: node.id,
        assetType: String(data.assetType ?? '') as ConfigAsset['assetType'],
        name: String(data.name ?? node.id),
        preset: String(data.preset ?? 'Default'),
        color: String(data.color ?? '#cccccc'),
        x: Number(node.position.x ?? 0),
        y: Number(node.position.y ?? 0),
        params,
      };
    });
}

export function nodesToPipes(nodes: Node[], edges: Edge[]): ConfigPipe[] {
  const pipes: ConfigPipe[] = [];

  for (const node of nodes) {
    if (!isPipeNode(node)) continue;

    const data = (node.data ?? {}) as AnyRecord;
    const incoming = new Map<number, string[]>();
    const outgoing = new Map<number, string[]>();

    for (const edge of edges) {
      if (edge.target === node.id) {
        const idx = handleIndex(String(edge.targetHandle ?? ''), 'in_');
        const sourcePort = String(edge.sourceHandle ?? '');
        if (idx === null || !sourcePort) continue;
        const refs = incoming.get(idx) ?? [];
        refs.push(`${edge.source}.${sourcePort}`);
        incoming.set(idx, refs);
      }

      if (edge.source === node.id) {
        const idx = handleIndex(String(edge.sourceHandle ?? ''), 'out_');
        const targetPort = String(edge.targetHandle ?? '');
        if (idx === null || !targetPort) continue;
        const refs = outgoing.get(idx) ?? [];
        refs.push(`${edge.target}.${targetPort}`);
        outgoing.set(idx, refs);
      }
    }

    pipes.push({
      id: node.id,
      x: Number(node.position.x ?? 0),
      y: Number(node.position.y ?? 0),
      medium: normalizeMedium(data.medium),
      in: toSortedGroups(incoming),
      out: toSortedGroups(outgoing),
    });
  }

  return pipes;
}

export function serializeConfigYaml(nodes: Node[], edges: Edge[]): string {
  const assets = nodesToAssets(nodes).map((a) => ({
    id: a.id,
    asset_type: a.assetType,
    name: a.name,
    pos: [Number(a.x.toFixed(2)), Number(a.y.toFixed(2))],
    preset: a.preset,
    color: a.color,
    ...a.params,
  }));

  const pipes = nodesToPipes(nodes, edges).map((p) => ({
    id: p.id,
    pos: [Number(p.x.toFixed(2)), Number(p.y.toFixed(2))],
    medium: p.medium,
    in: p.in,
    out: p.out,
  }));

  return yaml.dump({ assets, pipes }, { noRefs: true, sortKeys: false });
}

export function parseConfigYaml(text: string): { assets: ConfigAsset[]; pipes: ConfigPipe[] } {
  const parsed = (yaml.load(text) ?? {}) as AnyRecord;

  const assetsRaw = parsed.assets;
  const assets: ConfigAsset[] = [];

  if (Array.isArray(assetsRaw)) {
    for (const item of assetsRaw) {
      if (!item || typeof item !== 'object') continue;
      const obj = item as AnyRecord;
      const pos = Array.isArray(obj.pos) ? obj.pos : [obj.x, obj.y];
      const assetType = String(obj.asset_type ?? '').trim();
      if (!assetType) continue;

      assets.push({
        id: String(obj.id ?? crypto.randomUUID()),
        assetType: assetType as ConfigAsset['assetType'],
        name: String(obj.name ?? 'Asset'),
        preset: String(obj.preset ?? 'Default'),
        color: String(obj.color ?? '#cccccc'),
        x: Number(pos?.[0] ?? 0),
        y: Number(pos?.[1] ?? 0),
        params: Object.fromEntries(
          Object.entries(obj).filter(
            ([k]) => !['id', 'asset_type', 'name', 'preset', 'color', 'pos', 'x', 'y'].includes(k)
          )
        ) as ConfigAsset['params'],
      });
    }
  }

  const pipesRaw = parsed.pipes;
  const pipes: ConfigPipe[] = [];
  if (Array.isArray(pipesRaw)) {
    for (const item of pipesRaw) {
      if (!item || typeof item !== 'object') continue;
      const obj = item as AnyRecord;
      const pos = Array.isArray(obj.pos) ? obj.pos : [obj.x, obj.y];

      const inGroups = normalizeGroups(obj.in);
      const outGroups = normalizeGroups(obj.out);

      pipes.push({
        id: String(obj.id ?? crypto.randomUUID()),
        x: Number(pos?.[0] ?? 0),
        y: Number(pos?.[1] ?? 0),
        medium: normalizeMedium(obj.medium),
        in: inGroups,
        out: outGroups,
      });
    }
  }

  return { assets, pipes };
}
