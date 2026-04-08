import { useEffect, useMemo, useRef, useState } from 'react';
import ReactFlow, {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  Background,
  EdgeProps,
  Connection,
  Controls,
  Edge,
  Handle,
  MarkerType,
  MiniMap,
  Node,
  OnEdgesChange,
  OnNodesChange,
  Position,
} from 'reactflow';
import { v4 as uuidv4 } from 'uuid';
import { fallbackAssetCatalog } from './assetCatalog';
import { parseConfigYaml, serializeConfigYaml } from './configCodec';
import { AssetPort, AssetType, AssetUiMeta, ConfigAsset, Medium } from './types';

const API_URL = '/api';

type AssetParams = Record<string, string | number | boolean>;
type AssetNodeData = {
  kind: 'asset';
  assetType: AssetType;
  name: string;
  preset: string;
  params: AssetParams;
  color: string;
  ports: {
    in: AssetPort[];
    out: AssetPort[];
  };
};

type PipeNodeData = {
  kind: 'pipe';
  medium: Medium;
  ports: {
    in: AssetPort[];
    out: AssetPort[];
  };
  connectionCounts: {
    in: Record<string, number>;
    out: Record<string, number>;
  };
};

type NodeData = AssetNodeData | PipeNodeData;

type RoutePoint = {
  x: number;
  y: number;
};

type RouteCut = {
  segmentIndex: number;
  position: number;
  orientation: 'h' | 'v';
};

type RoutedEdgeData = {
  medium: Medium;
  route?: RoutePoint[];
  cuts?: RouteCut[];
  fragments?: RoutePoint[][];
  startControlDistancePx?: number;
  endControlDistancePx?: number;
};

const MEDIUM_ORDER: Record<Medium, number> = {
  electric: 0,
  thermal: 1,
  monetary: 2,
  data: 3,
};

const PORT_SPACING_PX = 18;
const PORT_VERTICAL_MARGIN_PX = 12;
const ASSET_MIN_HEIGHT_PX = 34;
const PIPE_MIN_HEIGHT_PX = 16;
const PIPE_WIDTH_PX = 24;
const HANDLE_OUTER_OFFSET_PX = 10;
const ROUTE_STUB_PX = 40;
const ROUTE_GRID_PX = 16;
const ROUTE_OBSTACLE_PADDING_PX = 18;
const ROUTE_CORNER_RADIUS_PX = 14;
const EDGE_CUT_GAP_PX = 8;
const ROUTE_MIN_SEGMENT_GAP_PX = 18;
const ROUTE_SELF_CONTROL_BOOST_STEP_PX = 18;
const ROUTE_SELF_CONTROL_MAX_PX = 220;

const EDGE_ARROW = {
  type: MarkerType.ArrowClosed,
  width: 22,
  height: 22,
};

function normalizeMedium(raw: unknown): Medium {
  const value = String(raw ?? '').trim().toLowerCase();
  if (value === 'data') return 'data';
  if (value === 'electric' || value === 'thermal' || value === 'monetary') return value as Medium;
  return 'electric';
}

function sortPortsByMedium(ports: AssetPort[]): AssetPort[] {
  return [...ports].sort((a, b) => {
    const mediumDiff = MEDIUM_ORDER[normalizeMedium(a.medium)] - MEDIUM_ORDER[normalizeMedium(b.medium)];
    if (mediumDiff !== 0) return mediumDiff;
    return a.id.localeCompare(b.id);
  });
}

function centeredAxisPosition(index: number, total: number): string {
  const offset = (index - (total - 1) / 2) * PORT_SPACING_PX;
  if (offset === 0) return '50%';
  const sign = offset > 0 ? '+' : '-';
  return `calc(50% ${sign} ${Math.abs(offset)}px)`;
}

function requiredNodeHeight(portCount: number, minHeightPx: number): number {
  const ports = Math.max(portCount, 1);
  return Math.max(minHeightPx, PORT_VERTICAL_MARGIN_PX * 2 + PORT_SPACING_PX * (ports - 1));
}

function mediumColor(medium: Medium): string {
  if (medium === 'electric') return '#2a9d8f';
  if (medium === 'thermal') return '#f4a261';
  if (medium === 'monetary') return '#457b9d';
  return '#6b7280';
}

function edgeStyle(medium: Medium) {
  return {
    stroke: mediumColor(medium),
    strokeWidth: 2.25,
  };
}

function edgeMarker(medium: Medium) {
  return {
    ...EDGE_ARROW,
    color: mediumColor(medium),
  };
}

function assetNodeStyle(color: string, name: string, portCount: number) {
  const width = estimateAssetWidth(name);
  return {
    background: color,
    border: '2px solid #1f2937',
    borderRadius: '12px',
    padding: '0',
    color: '#102a43',
    textAlign: 'center' as const,
    fontWeight: 600,
    whiteSpace: 'nowrap' as const,
    width: `${width}px`,
    minHeight: `${requiredNodeHeight(portCount, ASSET_MIN_HEIGHT_PX)}px`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'visible' as const,
  };
}

function pipeNodeStyle(medium: Medium, heightPx: number) {
  return {
    background: '#ffffff',
    border: `2px solid ${mediumColor(medium)}`,
    borderRadius: '999px',
    padding: '0',
    width: `${PIPE_WIDTH_PX}px`,
    minHeight: `${heightPx}px`,
    color: '#0f172a',
    textAlign: 'center' as const,
    fontWeight: 700,
    whiteSpace: 'nowrap' as const,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'visible' as const,
  };
}

function getPortsForType(assetType: string, catalog: Record<string, AssetUiMeta>) {
  const ports = catalog[assetType]?.ports;
  return {
    in: sortPortsByMedium(ports?.in ?? []),
    out: sortPortsByMedium(ports?.out ?? []),
  };
}

function buildPriorityPorts(prefix: 'in' | 'out', medium: Medium, usedCount: number): AssetPort[] {
  const count = Math.max(1, usedCount + 1);
  return Array.from({ length: count }, (_, index) => ({
    id: `${prefix}_${index + 1}`,
    medium,
    label: `${prefix === 'in' ? 'In' : 'Out'} ${index + 1}`,
    description: `${prefix === 'in' ? 'Input' : 'Output'} priority ${index + 1}`,
  }));
}

function buildPipePorts(medium: Medium, usedIn: number, usedOut: number): PipeNodeData['ports'] {
  return {
    in: buildPriorityPorts('in', medium, usedIn),
    out: buildPriorityPorts('out', medium, usedOut),
  };
}

function isPipeNode(node: Node<NodeData>): node is Node<PipeNodeData> {
  return node.data.kind === 'pipe';
}

function handleIndex(handle: string, prefix: 'in_' | 'out_'): number | null {
  if (!handle.startsWith(prefix)) return null;
  const value = Number(handle.slice(prefix.length));
  if (!Number.isFinite(value) || value < 1) return null;
  return Math.floor(value);
}

function getPortMediumFromNode(node: Node<NodeData>, handleId: string, direction: 'source' | 'target'): Medium | null {
  const data = node.data;
  if (data.kind === 'pipe') {
    return normalizeMedium(data.medium);
  }

  const ports = direction === 'source' ? data.ports.out : data.ports.in;
  const port = ports.find((item) => item.id === handleId);
  if (!port) return null;
  return normalizeMedium(port.medium);
}

function buildAssetNode(
  id: string,
  x: number,
  y: number,
  assetType: string,
  name: string,
  preset: string,
  params: AssetParams,
  color: string,
  catalog: Record<string, AssetUiMeta>
): Node<AssetNodeData> {
  const ports = getPortsForType(assetType, catalog);
  const maxPortCount = Math.max(ports.in.length, ports.out.length, 1);
  return {
    id,
    position: { x, y },
    type: 'asset',
    data: {
      kind: 'asset',
      assetType,
      name,
      preset,
      params,
      color,
      ports,
    },
    style: assetNodeStyle(color, name, maxPortCount),
  };
}

function buildPipeNode(
  id: string,
  x: number,
  y: number,
  medium: Medium,
  usedIn: number,
  usedOut: number
): Node<PipeNodeData> {
  const normalized = normalizeMedium(medium);
  const ports = buildPipePorts(normalized, usedIn, usedOut);
  const maxPortCount = Math.max(ports.in.length, ports.out.length, 1);
  return {
    id,
    position: { x, y },
    type: 'pipe',
    data: {
      kind: 'pipe',
      medium: normalized,
      ports,
      connectionCounts: { in: {}, out: {} },
    },
    style: pipeNodeStyle(normalized, requiredNodeHeight(maxPortCount, PIPE_MIN_HEIGHT_PX)),
  };
}

function estimateAssetWidth(label: string): number {
  return Math.max(92, 28 + label.trim().length * 8);
}

function getVisiblePorts(node: Node<NodeData>, direction: 'source' | 'target', medium: Medium): AssetPort[] {
  const ports = direction === 'source' ? node.data.ports.out : node.data.ports.in;
  return sortPortsByMedium(ports.filter((port) => normalizeMedium(port.medium) === medium));
}

function getNodeSize(node: Node<NodeData>, medium: Medium): { width: number; height: number } {
  if (node.data.kind === 'pipe') {
    const visiblePorts = getVisiblePorts(node, 'source', medium);
    const portCount = Math.max(visiblePorts.length, 1);
    const spread = PORT_SPACING_PX * (portCount - 1);
    const connectionCounts = node.data.connectionCounts ?? { in: {}, out: {} };
    const maxConnectionHeight = Math.max(
      12,
      ...Object.values(connectionCounts.in ?? {}).map((count) => 12 + (count - 1) * PORT_SPACING_PX),
      ...Object.values(connectionCounts.out ?? {}).map((count) => 12 + (count - 1) * PORT_SPACING_PX)
    );
    const height = Math.max(PIPE_MIN_HEIGHT_PX, spread + maxConnectionHeight);
    return {
      width: node.width ?? PIPE_WIDTH_PX,
      height: node.height ?? height,
    };
  }

  const visibleIn = getVisiblePorts(node, 'target', medium);
  const visibleOut = getVisiblePorts(node, 'source', medium);
  const portCount = Math.max(visibleIn.length, visibleOut.length, 1);

  return {
    width: node.width ?? estimateAssetWidth(node.data.name),
    height: node.height ?? requiredNodeHeight(portCount, ASSET_MIN_HEIGHT_PX),
  };
}

function getHandlePoint(
  node: Node<NodeData>,
  handleId: string,
  direction: 'source' | 'target',
  medium: Medium,
  laneOffsetY = 0
): RoutePoint {
  const ports = getVisiblePorts(node, direction, medium);
  const index = Math.max(0, ports.findIndex((port) => port.id === handleId));
  const total = Math.max(ports.length, 1);
  const centeredOffset = (index - (total - 1) / 2) * PORT_SPACING_PX;
  const { width, height } = getNodeSize(node, medium);

  return {
    x: node.position.x + (direction === 'source' ? width + HANDLE_OUTER_OFFSET_PX : -HANDLE_OUTER_OFFSET_PX),
    y: node.position.y + height / 2 + centeredOffset + laneOffsetY,
  };
}

function dedupeRoutePoints(points: RoutePoint[]): RoutePoint[] {
  const deduped: RoutePoint[] = [];
  for (const point of points) {
    const last = deduped[deduped.length - 1];
    if (!last || Math.abs(last.x - point.x) > 0.5 || Math.abs(last.y - point.y) > 0.5) {
      deduped.push(point);
    }
  }
  return deduped;
}

type RouteSegment = {
  edgeId: string;
  segmentIndex: number;
  from: RoutePoint;
  to: RoutePoint;
  orientation: 'h' | 'v';
};

type RouteRect = {
  nodeId: string;
  left: number;
  top: number;
  right: number;
  bottom: number;
};

type StraightLane = {
  x1: number;
  x2: number;
  y: number;
};

type PlannedRoute = {
  points: RoutePoint[];
  straightLane: StraightLane | null;
};

function getRouteSegments(edgeId: string, points: RoutePoint[]): RouteSegment[] {
  const segments: RouteSegment[] = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    const from = points[index];
    const to = points[index + 1];
    if (Math.abs(from.y - to.y) < 0.5) {
      segments.push({ edgeId, segmentIndex: index, from, to, orientation: 'h' });
      continue;
    }
    if (Math.abs(from.x - to.x) < 0.5) {
      segments.push({ edgeId, segmentIndex: index, from, to, orientation: 'v' });
    }
  }
  return segments;
}

function between(value: number, a: number, b: number): boolean {
  const min = Math.min(a, b);
  const max = Math.max(a, b);
  return value >= min && value <= max;
}

function pointAlongSegment(from: RoutePoint, orientation: 'h' | 'v', value: number): RoutePoint {
  return orientation === 'h' ? { x: value, y: from.y } : { x: from.x, y: value };
}

function getNodeBounds(node: Node<NodeData>, medium: Medium): RouteRect {
  const { width, height } = getNodeSize(node, medium);
  return {
    nodeId: node.id,
    left: node.position.x - ROUTE_OBSTACLE_PADDING_PX,
    top: node.position.y - ROUTE_OBSTACLE_PADDING_PX,
    right: node.position.x + width + ROUTE_OBSTACLE_PADDING_PX,
    bottom: node.position.y + height + ROUTE_OBSTACLE_PADDING_PX,
  };
}

function getNodeBodyBounds(node: Node<NodeData>, medium: Medium): RouteRect {
  const { width, height } = getNodeSize(node, medium);
  return {
    nodeId: node.id,
    left: node.position.x,
    top: node.position.y,
    right: node.position.x + width,
    bottom: node.position.y + height,
  };
}

function rangeOverlaps(a1: number, a2: number, b1: number, b2: number, margin = 0): boolean {
  const leftA = Math.min(a1, a2) - margin;
  const rightA = Math.max(a1, a2) + margin;
  const leftB = Math.min(b1, b2);
  const rightB = Math.max(b1, b2);
  return rightA >= leftB && rightB >= leftA;
}

function pointInsideRect(point: RoutePoint, rect: RouteRect): boolean {
  return point.x > rect.left && point.x < rect.right && point.y > rect.top && point.y < rect.bottom;
}

function cubicPoint(p0: RoutePoint, c1: RoutePoint, c2: RoutePoint, p3: RoutePoint, t: number): RoutePoint {
  const it = 1 - t;
  const a = it * it * it;
  const b = 3 * it * it * t;
  const c = 3 * it * t * t;
  const d = t * t * t;
  return {
    x: a * p0.x + b * c1.x + c * c2.x + d * p3.x,
    y: a * p0.y + b * c1.y + c * c2.y + d * p3.y,
  };
}

function controlDistance(fromX: number, toX: number): number {
  const distance = Math.abs(toX - fromX);
  return Math.max(ROUTE_CORNER_RADIUS_PX + 10, Math.min(96, distance * 0.45));
}

function curveHitsRects(start: RoutePoint, end: RoutePoint, rects: RouteRect[], distancePx: number): boolean {
  if (rects.length === 0) return false;

  const c1: RoutePoint = { x: start.x + distancePx, y: start.y };
  const c2: RoutePoint = { x: end.x - distancePx, y: end.y };

  for (let step = 1; step <= 36; step += 1) {
    const t = step / 36;
    if (t < 0.06 || t > 0.94) continue;
    const point = cubicPoint(start, c1, c2, end, t);
    if (rects.some((rect) => pointInsideRect(point, rect))) {
      return true;
    }
  }

  return false;
}

function controlDistanceAvoidingRects(start: RoutePoint, end: RoutePoint, rects: RouteRect[]): number {
  let distancePx = controlDistance(start.x, end.x);
  if (rects.length === 0) return distancePx;

  while (distancePx < ROUTE_SELF_CONTROL_MAX_PX && curveHitsRects(start, end, rects, distancePx)) {
    distancePx += ROUTE_SELF_CONTROL_BOOST_STEP_PX;
  }

  return Math.min(distancePx, ROUTE_SELF_CONTROL_MAX_PX);
}

function curveHitsObstacle(start: RoutePoint, end: RoutePoint, obstacles: RouteRect[]): boolean {
  const c1: RoutePoint = { x: start.x + controlDistance(start.x, end.x), y: start.y };
  const c2: RoutePoint = { x: end.x - controlDistance(start.x, end.x), y: end.y };

  for (let step = 1; step <= 36; step += 1) {
    const point = cubicPoint(start, c1, c2, end, step / 36);
    if (obstacles.some((rect) => pointInsideRect(point, rect))) {
      return true;
    }
  }

  return false;
}

function laneInterferes(
  y: number,
  x1: number,
  x2: number,
  obstacles: RouteRect[],
  usedSegments: StraightLane[]
): boolean {
  const blockedByNode = obstacles.some((rect) => {
    const yConflict = y >= rect.top - ROUTE_OBSTACLE_PADDING_PX && y <= rect.bottom + ROUTE_OBSTACLE_PADDING_PX;
    const xConflict = rangeOverlaps(x1, x2, rect.left, rect.right, ROUTE_OBSTACLE_PADDING_PX);
    return yConflict && xConflict;
  });

  if (blockedByNode) return true;

  return usedSegments.some((segment) => {
    if (!rangeOverlaps(x1, x2, segment.x1, segment.x2, ROUTE_GRID_PX)) return false;
    return Math.abs(y - segment.y) < ROUTE_MIN_SEGMENT_GAP_PX;
  });
}

function routeAroundObstacles(
  start: RoutePoint,
  end: RoutePoint,
  obstacles: RouteRect[],
  usedSegments: StraightLane[]
): PlannedRoute {
  if (!curveHitsObstacle(start, end, obstacles)) {
    return {
      points: dedupeRoutePoints([start, end]),
      straightLane: null,
    };
  }

  const x1 = Math.min(start.x, end.x) - ROUTE_STUB_PX;
  const x2 = Math.max(start.x, end.x) + ROUTE_STUB_PX;
  const upperPortY = Math.min(start.y, end.y);
  const baseY = upperPortY + PORT_VERTICAL_MARGIN_PX + ROUTE_GRID_PX;

  let selectedY = baseY;
  for (let step = 0; step < 120; step += 1) {
    const candidateY = baseY + step * ROUTE_GRID_PX;
    if (!laneInterferes(candidateY, x1, x2, obstacles, usedSegments)) {
      selectedY = candidateY;
      break;
    }
  }

  return {
    points: dedupeRoutePoints([
      start,
      { x: x1, y: selectedY },
      { x: x2, y: selectedY },
      end,
    ]),
    straightLane: { x1, x2, y: selectedY },
  };
}

function buildRouteFragments(points: RoutePoint[], cuts: RouteCut[]): RoutePoint[][] {
  if (points.length < 2) return [];

  const fragments: RoutePoint[][] = [];
  let current: RoutePoint[] = [points[0]];

  for (let segmentIndex = 0; segmentIndex < points.length - 1; segmentIndex += 1) {
    const from = points[segmentIndex];
    const to = points[segmentIndex + 1];
    if (Math.abs(from.y - to.y) >= 0.5 && Math.abs(from.x - to.x) >= 0.5) {
      if (current[current.length - 1]?.x !== to.x || current[current.length - 1]?.y !== to.y) {
        current.push(to);
      }
      continue;
    }
    const orientation: 'h' | 'v' = Math.abs(from.y - to.y) < 0.5 ? 'h' : 'v';
    const segmentCuts = cuts
      .filter((cut) => cut.segmentIndex === segmentIndex && cut.orientation === orientation)
      .sort((a, b) => a.position - b.position);

    let cursor = orientation === 'h' ? from.x : from.y;
    const endValue = orientation === 'h' ? to.x : to.y;
    const ascending = endValue >= cursor;

    for (const cut of segmentCuts) {
      const cutStartValue = cut.position - EDGE_CUT_GAP_PX;
      const cutEndValue = cut.position + EDGE_CUT_GAP_PX;
      const beforeCut = ascending ? Math.max(cursor, Math.min(cutStartValue, endValue)) : Math.min(cursor, Math.max(cutStartValue, endValue));
      const afterCut = ascending ? Math.min(cutEndValue, endValue) : Math.max(cutEndValue, endValue);

      if (ascending ? beforeCut > cursor + 0.5 : beforeCut < cursor - 0.5) {
        current.push(pointAlongSegment(from, orientation, beforeCut));
      }

      if (current.length > 1) {
        fragments.push(current);
      }

      current = [pointAlongSegment(from, orientation, afterCut)];
      cursor = afterCut;
    }

    if (ascending ? cursor < endValue - 0.5 : cursor > endValue + 0.5) {
      current.push(to);
    } else if (current[current.length - 1]?.x !== to.x || current[current.length - 1]?.y !== to.y) {
      current.push(to);
    }
  }

  if (current.length > 1) {
    fragments.push(current);
  }

  return fragments;
}

function pointsToSmoothPath(
  points: RoutePoint[],
  controlOptions?: {
    startControlDistancePx?: number;
    endControlDistancePx?: number;
  }
): string {
  if (points.length < 2) return '';

  const horizontalControl = (fromX: number, toX: number): number => controlDistance(fromX, toX);

  if (points.length === 2) {
    const start = points[0];
    const end = points[1];
    const startControlDistancePx = controlOptions?.startControlDistancePx ?? horizontalControl(start.x, end.x);
    const endControlDistancePx = controlOptions?.endControlDistancePx ?? horizontalControl(start.x, end.x);
    const startControl: RoutePoint = {
      x: start.x + startControlDistancePx,
      y: start.y,
    };
    const endControl: RoutePoint = {
      x: end.x - endControlDistancePx,
      y: end.y,
    };
    return `M ${start.x} ${start.y} C ${startControl.x} ${startControl.y} ${endControl.x} ${endControl.y} ${end.x} ${end.y}`;
  }

  if (points.length === 4 && Math.abs(points[1].y - points[2].y) < 0.5) {
    const start = points[0];
    const firstJoin = points[1];
    const secondJoin = points[2];
    const end = points[3];
    const laneDir = secondJoin.x >= firstJoin.x ? 1 : -1;
    const startControlDistancePx = controlOptions?.startControlDistancePx ?? horizontalControl(start.x, firstJoin.x);
    const endControlDistancePx = controlOptions?.endControlDistancePx ?? horizontalControl(secondJoin.x, end.x);

    const c1: RoutePoint = {
      x: start.x + startControlDistancePx,
      y: start.y,
    };
    const c2: RoutePoint = {
      x: firstJoin.x - laneDir * startControlDistancePx,
      y: firstJoin.y,
    };
    const c3: RoutePoint = {
      x: secondJoin.x + laneDir * endControlDistancePx,
      y: secondJoin.y,
    };
    const c4: RoutePoint = {
      x: end.x - endControlDistancePx,
      y: end.y,
    };

    return [
      `M ${start.x} ${start.y}`,
      `C ${c1.x} ${c1.y} ${c2.x} ${c2.y} ${firstJoin.x} ${firstJoin.y}`,
      `L ${secondJoin.x} ${secondJoin.y}`,
      `C ${c3.x} ${c3.y} ${c4.x} ${c4.y} ${end.x} ${end.y}`,
    ].join(' ');
  }

  const commands: string[] = [`M ${points[0].x} ${points[0].y}`];
  const smoothness = Math.min(0.32, Math.max(0.18, ROUTE_CORNER_RADIUS_PX / 48));

  for (let index = 0; index < points.length - 1; index += 1) {
    const p0 = points[Math.max(index - 1, 0)];
    const p1 = points[index];
    const p2 = points[index + 1];
    const p3 = points[Math.min(index + 2, points.length - 1)];

    const control1 = {
      x: p1.x + ((p2.x - p0.x) / 6) * smoothness,
      y: p1.y + ((p2.y - p0.y) / 6) * smoothness,
    };

    const control2 = {
      x: p2.x - ((p3.x - p1.x) / 6) * smoothness,
      y: p2.y - ((p3.y - p1.y) / 6) * smoothness,
    };

    commands.push(`C ${control1.x} ${control1.y} ${control2.x} ${control2.y} ${p2.x} ${p2.y}`);
  }
  return commands.join(' ');
}

function mapEdgesWithRouting(
  nodes: Node<NodeData>[],
  edges: Edge<RoutedEdgeData>[],
  medium: Medium
): Edge<RoutedEdgeData>[] {
  if (edges.length === 0) return edges;

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const sourceBuckets = new Map<string, string[]>();
  const targetBuckets = new Map<string, string[]>();

  for (const edge of edges) {
    const sourceKey = `${edge.source}|${String(edge.sourceHandle ?? '')}`;
    const targetKey = `${edge.target}|${String(edge.targetHandle ?? '')}`;

    const sourceList = sourceBuckets.get(sourceKey) ?? [];
    sourceList.push(edge.id);
    sourceBuckets.set(sourceKey, sourceList);

    const targetList = targetBuckets.get(targetKey) ?? [];
    targetList.push(edge.id);
    targetBuckets.set(targetKey, targetList);
  }

  for (const list of sourceBuckets.values()) list.sort();
  for (const list of targetBuckets.values()) list.sort();

  const usedStraightSegments: StraightLane[] = [];

  const routed = edges.map((edge) => {
    const sourceNode = nodeById.get(edge.source);
    const targetNode = nodeById.get(edge.target);
    const sourceHandle = String(edge.sourceHandle ?? '');
    const targetHandle = String(edge.targetHandle ?? '');

    if (!sourceNode || !targetNode || !sourceHandle || !targetHandle) {
      return edge;
    }

    const sourceKey = `${edge.source}|${sourceHandle}`;
    const targetKey = `${edge.target}|${targetHandle}`;
    const sourceIds = sourceBuckets.get(sourceKey) ?? [edge.id];
    const targetIds = targetBuckets.get(targetKey) ?? [edge.id];
    const sourceLane = sourceIds.indexOf(edge.id) - (sourceIds.length - 1) / 2;
    const targetLane = targetIds.indexOf(edge.id) - (targetIds.length - 1) / 2;

    const sourceLaneOffsetY = isPipeNode(sourceNode) ? sourceLane * PORT_SPACING_PX : 0;
    const targetLaneOffsetY = isPipeNode(targetNode) ? targetLane * PORT_SPACING_PX : 0;
    const startBase = getHandlePoint(sourceNode, sourceHandle, 'source', medium);
    const endBase = getHandlePoint(targetNode, targetHandle, 'target', medium);
    const start: RoutePoint = { x: startBase.x, y: startBase.y + sourceLaneOffsetY };
    const end: RoutePoint = { x: endBase.x, y: endBase.y + targetLaneOffsetY };

    const obstacleRects = nodes
      .filter((node) => node.id !== sourceNode.id && node.id !== targetNode.id)
      .map((node) => getNodeBounds(node, medium));
    const sourceBodyRect = getNodeBodyBounds(sourceNode, medium);
    const targetBodyRect = getNodeBodyBounds(targetNode, medium);

    const plannedRoute = routeAroundObstacles(start, end, obstacleRects, usedStraightSegments);
    if (plannedRoute.straightLane) {
      usedStraightSegments.push(plannedRoute.straightLane);
    }

    let startControlDistancePx: number | undefined;
    let endControlDistancePx: number | undefined;
    if (plannedRoute.points.length === 2) {
      const distancePx = controlDistanceAvoidingRects(start, end, [sourceBodyRect, targetBodyRect]);
      startControlDistancePx = distancePx;
      endControlDistancePx = distancePx;
    } else if (plannedRoute.points.length === 4 && Math.abs(plannedRoute.points[1].y - plannedRoute.points[2].y) < 0.5) {
      startControlDistancePx = controlDistanceAvoidingRects(plannedRoute.points[0], plannedRoute.points[1], [sourceBodyRect]);
      endControlDistancePx = controlDistanceAvoidingRects(plannedRoute.points[2], plannedRoute.points[3], [targetBodyRect]);
    }

    return {
      ...edge,
      type: 'routed',
      style: edgeStyle(medium),
      markerEnd: edgeMarker(medium),
      data: {
        ...(edge.data ?? {}),
        medium,
        route: plannedRoute.points,
        startControlDistancePx,
        endControlDistancePx,
      },
    };
  });

  const segmentsByEdge = new Map<string, RouteSegment[]>();
  for (const edge of routed) {
    const points = edge.data?.route;
    if (!points || points.length < 2) continue;
    segmentsByEdge.set(edge.id, getRouteSegments(edge.id, points));
  }

  const cutsByEdge = new Map<string, RouteCut[]>();
  const edgeIds = routed.map((edge) => edge.id);

  for (let i = 0; i < edgeIds.length; i += 1) {
    const edgeAId = edgeIds[i];
    const segmentsA = segmentsByEdge.get(edgeAId) ?? [];

    for (let j = i + 1; j < edgeIds.length; j += 1) {
      const edgeBId = edgeIds[j];
      const segmentsB = segmentsByEdge.get(edgeBId) ?? [];

      for (const segmentA of segmentsA) {
        for (const segmentB of segmentsB) {
          if (segmentA.orientation === segmentB.orientation) continue;

          const horizontal = segmentA.orientation === 'h' ? segmentA : segmentB;
          const vertical = segmentA.orientation === 'v' ? segmentA : segmentB;
          const ix = vertical.from.x;
          const iy = horizontal.from.y;

          if (!between(ix, horizontal.from.x, horizontal.to.x)) continue;
          if (!between(iy, vertical.from.y, vertical.to.y)) continue;

          const horizontalEndpointDist = Math.min(
            Math.abs(ix - horizontal.from.x),
            Math.abs(ix - horizontal.to.x)
          );
          const verticalEndpointDist = Math.min(
            Math.abs(iy - vertical.from.y),
            Math.abs(iy - vertical.to.y)
          );

          if (horizontalEndpointDist <= EDGE_CUT_GAP_PX + 1 || verticalEndpointDist <= EDGE_CUT_GAP_PX + 1) {
            continue;
          }

          const underEdgeId = edgeAId > edgeBId ? edgeAId : edgeBId;
          const underSegment = underEdgeId === horizontal.edgeId ? horizontal : vertical;
          const cutPosition = underSegment.orientation === 'h' ? ix : iy;
          const cutList = cutsByEdge.get(underEdgeId) ?? [];
          const alreadyPresent = cutList.some(
            (cut) =>
              cut.segmentIndex === underSegment.segmentIndex &&
              cut.orientation === underSegment.orientation &&
              Math.abs(cut.position - cutPosition) < 2
          );
          if (alreadyPresent) continue;

          cutList.push({
            segmentIndex: underSegment.segmentIndex,
            position: cutPosition,
            orientation: underSegment.orientation,
          });
          cutsByEdge.set(underEdgeId, cutList);
        }
      }
    }
  }

  return routed.map((edge) => {
    const cuts = cutsByEdge.get(edge.id) ?? [];
    const fragments = buildRouteFragments(edge.data?.route ?? [], cuts);
    return {
      ...edge,
      data: {
        ...(edge.data ?? { medium: 'electric' }),
        cuts,
        route: edge.data?.route ?? [],
        fragments,
        startControlDistancePx: edge.data?.startControlDistancePx,
        endControlDistancePx: edge.data?.endControlDistancePx,
      },
    };
  });
}

function RoutedEdge({
  id,
  data,
  sourceX,
  sourceY,
  targetX,
  targetY,
  markerEnd,
}: EdgeProps<RoutedEdgeData>) {
  const medium = normalizeMedium(data?.medium ?? 'electric');
  const color = mediumColor(medium);
  const points = data?.route && data.route.length >= 2 ? data.route : [
    { x: sourceX, y: sourceY },
    { x: targetX, y: targetY },
  ];
  const fragments = data?.fragments && data.fragments.length > 0 ? data.fragments : [points];

  return (
    <g>
      {fragments.map((fragment, index) => {
        const path = pointsToSmoothPath(fragment, {
          startControlDistancePx: index === 0 ? data?.startControlDistancePx : undefined,
          endControlDistancePx: index === fragments.length - 1 ? data?.endControlDistancePx : undefined,
        });
        if (!path) return null;

        return (
          <path
            key={`${id}-${index}`}
            className="react-flow__edge-path"
            d={path}
            stroke={color}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            markerEnd={index === fragments.length - 1 ? markerEnd : undefined}
          />
        );
      })}
    </g>
  );
}

function defaultNodes(catalog: Record<string, AssetUiMeta>): Node<NodeData>[] {
  const pvMeta = catalog.pv ?? fallbackAssetCatalog.pv;
  const elMeta = catalog.el ?? fallbackAssetCatalog.el;
  const grdMeta = catalog.grd ?? fallbackAssetCatalog.grd;

  const pvId = `pv_${uuidv4().slice(0, 8)}`;
  const loadId = `el_${uuidv4().slice(0, 8)}`;
  const gridId = `grd_${uuidv4().slice(0, 8)}`;

  return [
    buildAssetNode(pvId, 120, 120, 'pv', 'PV 1', 'Default', { ...(pvMeta.presets.Default ?? {}) }, pvMeta.color, catalog),
    buildAssetNode(loadId, 600, 100, 'el', 'Load 1', 'Default', { ...(elMeta.presets.Default ?? {}) }, elMeta.color, catalog),
    buildAssetNode(gridId, 600, 280, 'grd', 'Grid', 'Default', { ...(grdMeta.presets.Default ?? {}) }, grdMeta.color, catalog),
  ];
}

function syncPipeGraph(
  nodes: Node<NodeData>[],
  edges: Edge<RoutedEdgeData>[],
  medium: Medium
): { nodes: Node<NodeData>[]; edges: Edge<RoutedEdgeData>[]; changed: boolean } {
  const selectedMedium = normalizeMedium(medium);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  const visibleNodes = nodes
    .filter((node) => node.data.kind === 'asset' || normalizeMedium(node.data.medium) === selectedMedium)
    .map((node) => {
      if (node.data.kind === 'asset') {
        const visibleIn = getVisiblePorts(node, 'target', selectedMedium);
        const visibleOut = getVisiblePorts(node, 'source', selectedMedium);
        const portCount = Math.max(visibleIn.length, visibleOut.length, 1);
        return {
          ...node,
          data: {
            ...node.data,
            ports: {
              in: visibleIn,
              out: visibleOut,
            },
          },
          style: {
            ...assetNodeStyle(node.data.color, node.data.name, portCount),
          },
        };
      }

      const visibleIn = getVisiblePorts(node, 'target', selectedMedium);
      const visibleOut = getVisiblePorts(node, 'source', selectedMedium);
      const connectionCounts = node.data.connectionCounts ?? { in: {}, out: {} };
      const portCount = Math.max(visibleIn.length, visibleOut.length, 1);
      const maxConnectionHeight = Math.max(
        12,
        ...Object.values(connectionCounts.in ?? {}).map((count) => 12 + (count - 1) * PORT_SPACING_PX),
        ...Object.values(connectionCounts.out ?? {}).map((count) => 12 + (count - 1) * PORT_SPACING_PX)
      );

      return {
        ...node,
        data: {
          ...node.data,
          ports: {
            in: visibleIn,
            out: visibleOut,
          },
          connectionCounts,
        },
        style: {
            ...pipeNodeStyle(selectedMedium, Math.max(requiredNodeHeight(portCount, PIPE_MIN_HEIGHT_PX), portCount > 0 ? portCount * PORT_SPACING_PX + maxConnectionHeight : maxConnectionHeight)),
        },
      };
    });

  const visibleNodeById = new Map(visibleNodes.map((node) => [node.id, node]));

  const visibleEdges: Edge<RoutedEdgeData>[] = [];
  for (const edge of edges) {
    const sourceNode = nodeById.get(edge.source);
    const targetNode = nodeById.get(edge.target);
    if (!sourceNode || !targetNode) continue;

    const sourceMedium = getPortMediumFromNode(sourceNode, String(edge.sourceHandle ?? ''), 'source');
    const targetMedium = getPortMediumFromNode(targetNode, String(edge.targetHandle ?? ''), 'target');
    if (!sourceMedium || sourceMedium !== targetMedium || sourceMedium !== selectedMedium) continue;

    if (!visibleNodeById.has(edge.source) || !visibleNodeById.has(edge.target)) continue;

    const sourceIsPipe = isPipeNode(sourceNode);
    const targetIsPipe = isPipeNode(targetNode);
    if (sourceIsPipe === targetIsPipe) continue;

    const sourceHandle = String(edge.sourceHandle ?? '');
    const targetHandle = String(edge.targetHandle ?? '');
    if (!sourceHandle || !targetHandle) continue;

    if (sourceIsPipe && handleIndex(sourceHandle, 'out_') === null) continue;
    if (targetIsPipe && handleIndex(targetHandle, 'in_') === null) continue;

    visibleEdges.push({
      ...edge,
      type: 'routed',
      style: edgeStyle(selectedMedium),
      markerEnd: edgeMarker(selectedMedium),
      data: {
        ...(edge.data ?? {}),
        medium: selectedMedium,
      },
    });
  }

  const routedEdges = mapEdgesWithRouting(visibleNodes, visibleEdges, selectedMedium);

  const pipeConnectionCounts = new Map<string, { in: Record<string, number>; out: Record<string, number> }>();
  routedEdges.forEach((edge) => {
    const sourceNode = visibleNodeById.get(edge.source);
    const targetNode = visibleNodeById.get(edge.target);
    if (sourceNode && isPipeNode(sourceNode)) {
      const bucket = pipeConnectionCounts.get(sourceNode.id) ?? { in: {}, out: {} };
      const key = String(edge.sourceHandle ?? '');
      if (key) bucket.out[key] = (bucket.out[key] ?? 0) + 1;
      pipeConnectionCounts.set(sourceNode.id, bucket);
    }
    if (targetNode && isPipeNode(targetNode)) {
      const bucket = pipeConnectionCounts.get(targetNode.id) ?? { in: {}, out: {} };
      const key = String(edge.targetHandle ?? '');
      if (key) bucket.in[key] = (bucket.in[key] ?? 0) + 1;
      pipeConnectionCounts.set(targetNode.id, bucket);
    }
  });

  const nextNodes = visibleNodes.map((node) => {
    if (!isPipeNode(node)) {
      return node;
    }

    const counts = pipeConnectionCounts.get(node.id) ?? { in: {}, out: {} };
    const maxConnectionHeight = Math.max(
      12,
      ...Object.values(counts.in ?? {}).map((count) => 12 + (count - 1) * PORT_SPACING_PX),
      ...Object.values(counts.out ?? {}).map((count) => 12 + (count - 1) * PORT_SPACING_PX)
    );
    const portCount = Math.max(node.data.ports.in.length, node.data.ports.out.length, 1);

    return {
      ...node,
      data: {
        ...node.data,
        connectionCounts: counts,
      },
      style: {
        ...pipeNodeStyle(selectedMedium, Math.max(requiredNodeHeight(portCount, PIPE_MIN_HEIGHT_PX), portCount * PORT_SPACING_PX + maxConnectionHeight)),
      },
    };
  });

  const nextEdges = mapEdgesWithRouting(nextNodes, routedEdges, selectedMedium);
  const currentSignature = JSON.stringify({ nodes, edges });
  const nextSignature = JSON.stringify({ nodes: nextNodes, edges: nextEdges });
  return { nodes: nextNodes, edges: nextEdges, changed: currentSignature !== nextSignature };
}

function AssetNode({ data, activeMedium }: { data: AssetNodeData; activeMedium?: Medium }) {
  const inputPorts = sortPortsByMedium(
    activeMedium ? data.ports.in.filter((port) => normalizeMedium(port.medium) === activeMedium) : data.ports.in
  );
  const outputPorts = sortPortsByMedium(
    activeMedium ? data.ports.out.filter((port) => normalizeMedium(port.medium) === activeMedium) : data.ports.out
  );

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {inputPorts.map((port, idx) => {
        const top = centeredAxisPosition(idx, inputPorts.length);
        const tooltip = `${port.description || port.label || port.id} (${port.medium})`;
        return (
          <Handle
            key={`in-${port.id}`}
            id={port.id}
            type="target"
            position={Position.Left}
            title={tooltip}
            style={{
              left: '0%',
              top,
              transform: 'translate(-100%, -50%)',
              width: 10,
              height: 10,
              background: mediumColor(normalizeMedium(port.medium)),
              border: '1px solid #0f172a',
            }}
          />
        );
      })}

      <div style={{ padding: '8px 12px' }}>{data.name}</div>

      {outputPorts.map((port, idx) => {
        const top = centeredAxisPosition(idx, outputPorts.length);
        const tooltip = `${port.description || port.label || port.id} (${port.medium})`;
        return (
          <Handle
            key={`out-${port.id}`}
            id={port.id}
            type="source"
            position={Position.Right}
            title={tooltip}
            style={{
              left: '100%',
              top,
              transform: 'translate(0%, -50%)',
              width: 10,
              height: 10,
              background: mediumColor(normalizeMedium(port.medium)),
              border: '1px solid #0f172a',
            }}
          />
        );
      })}
    </div>
  );
}

function PipeNode({ data, activeMedium }: { data: PipeNodeData; activeMedium?: Medium }) {
  const inputPorts = sortPortsByMedium(
    activeMedium ? data.ports.in.filter((port) => normalizeMedium(port.medium) === activeMedium) : data.ports.in
  );
  const outputPorts = sortPortsByMedium(
    activeMedium ? data.ports.out.filter((port) => normalizeMedium(port.medium) === activeMedium) : data.ports.out
  );

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {inputPorts.map((port, idx) => {
        const top = centeredAxisPosition(idx, inputPorts.length);
        const tooltip = `${port.description || port.label || port.id} (${port.medium})`;
        const connectionCount = Math.max(1, data.connectionCounts?.in?.[port.id] ?? 1);
        const handleHeight = 12 + (connectionCount - 1) * PORT_SPACING_PX;
        return (
          <Handle
            key={`in-${port.id}`}
            id={port.id}
            type="target"
            position={Position.Left}
            title={tooltip}
            style={{
              left: '0%',
              top,
              transform: 'translate(-100%, -50%)',
              width: 10,
              height: handleHeight,
              borderRadius: '999px',
              background: mediumColor(normalizeMedium(port.medium)),
              border: '1px solid #0f172a',
            }}
          />
        );
      })}

      <div style={{ width: 1, height: 1 }} />

      {outputPorts.map((port, idx) => {
        const top = centeredAxisPosition(idx, outputPorts.length);
        const tooltip = `${port.description || port.label || port.id} (${port.medium})`;
        const connectionCount = Math.max(1, data.connectionCounts?.out?.[port.id] ?? 1);
        const handleHeight = 12 + (connectionCount - 1) * PORT_SPACING_PX;
        return (
          <Handle
            key={`out-${port.id}`}
            id={port.id}
            type="source"
            position={Position.Right}
            title={tooltip}
            style={{
              left: '100%',
              top,
              transform: 'translate(0%, -50%)',
              width: 10,
              height: handleHeight,
              borderRadius: '999px',
              background: mediumColor(normalizeMedium(port.medium)),
              border: '1px solid #0f172a',
            }}
          />
        );
      })}
    </div>
  );
}

function buildGraphFromConfig(
  assets: ConfigAsset[],
  pipes: ReturnType<typeof parseConfigYaml>['pipes'],
  catalog: Record<string, AssetUiMeta>
): { nodes: Node<NodeData>[]; edges: Edge<RoutedEdgeData>[] } {
  const assetNodes: Node<NodeData>[] = assets.map((asset) =>
    buildAssetNode(
      asset.id,
      asset.x,
      asset.y,
      asset.assetType,
      asset.name,
      asset.preset,
      asset.params,
      asset.color,
      catalog
    )
  );

  const pipeNodes: Node<NodeData>[] = pipes.map((pipe) =>
    buildPipeNode(
      pipe.id,
      pipe.x,
      pipe.y,
      normalizeMedium(pipe.medium),
      pipe.in.length,
      pipe.out.length
    )
  );

  const edges: Edge<RoutedEdgeData>[] = [];
  for (const pipe of pipes) {
    const medium = normalizeMedium(pipe.medium);

    pipe.in.forEach((group, groupIndex) => {
      group.forEach((ref, refIndex) => {
        const splitIndex = ref.indexOf('.');
        if (splitIndex <= 0 || splitIndex >= ref.length - 1) return;
        const source = ref.slice(0, splitIndex);
        const sourcePort = ref.slice(splitIndex + 1);
        edges.push({
          id: `${pipe.id}_in_${groupIndex + 1}_${refIndex + 1}`,
          source,
          target: pipe.id,
          sourceHandle: sourcePort,
          targetHandle: `in_${groupIndex + 1}`,
          type: 'routed',
          markerEnd: edgeMarker(medium),
          data: { medium },
          style: edgeStyle(medium),
        });
      });
    });

    pipe.out.forEach((group, groupIndex) => {
      group.forEach((ref, refIndex) => {
        const splitIndex = ref.indexOf('.');
        if (splitIndex <= 0 || splitIndex >= ref.length - 1) return;
        const target = ref.slice(0, splitIndex);
        const targetPort = ref.slice(splitIndex + 1);
        edges.push({
          id: `${pipe.id}_out_${groupIndex + 1}_${refIndex + 1}`,
          source: pipe.id,
          target,
          sourceHandle: `out_${groupIndex + 1}`,
          targetHandle: targetPort,
          type: 'routed',
          markerEnd: edgeMarker(medium),
          data: { medium },
          style: edgeStyle(medium),
        });
      });
    });
  }

  const synced = syncPipeGraph([...assetNodes, ...pipeNodes], edges, 'electric');
  return { nodes: synced.nodes, edges: synced.edges };
}

export default function App() {
  const [assetCatalog, setAssetCatalog] = useState<Record<string, AssetUiMeta>>(fallbackAssetCatalog);
  const [nodes, setNodes] = useState<Node<NodeData>[]>(() => defaultNodes(fallbackAssetCatalog));
  const [edges, setEdges] = useState<Edge<RoutedEdgeData>[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [assetTypeToAdd, setAssetTypeToAdd] = useState<string>('pv');
  const [currentFileName, setCurrentFileName] = useState<string>('simple');
  const [availableFiles, setAvailableFiles] = useState<string[]>([]);
  const [fileNameInput, setFileNameInput] = useState<string>('simple');
  const [selectedLoadFile, setSelectedLoadFile] = useState<string>('');
  const [activeMedium, setActiveMedium] = useState<Medium>('electric');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedNode = useMemo(() => nodes.find((node) => node.id === selectedNodeId) ?? null, [nodes, selectedNodeId]);
  useEffect(() => {
    const init = async () => {
      await fetchAssetCatalog();
      await fetchAvailableFiles();
      await loadFile('simple');
    };
    void init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setNodes((prev) =>
      prev.map((node) => {
        if (node.data.kind !== 'asset') return node;
        const ports = getPortsForType(String(node.data.assetType), assetCatalog);
        const maxPortCount = Math.max(ports.in.length, ports.out.length, 1);
        return {
          ...node,
          data: {
            ...node.data,
            ports,
          },
          style: assetNodeStyle(String(node.data.color ?? '#cccccc'), node.data.name, maxPortCount),
        };
      })
    );
  }, [assetCatalog]);

  useEffect(() => {
    const synced = syncPipeGraph(nodes, edges, 'electric');
    if (!synced.changed) return;
    setNodes(synced.nodes);
    setEdges(synced.edges);
  }, [nodes, edges]);

  const fetchAssetCatalog = async () => {
    try {
      const response = await fetch(`${API_URL}/asset-catalog`);
      if (!response.ok) throw new Error('Failed to fetch asset catalog');
      const data = await response.json();
      const catalog = data.catalog as Record<string, AssetUiMeta>;
      if (catalog && Object.keys(catalog).length > 0) {
        setAssetCatalog(catalog);
        if (!catalog[assetTypeToAdd]) {
          setAssetTypeToAdd(Object.keys(catalog)[0]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch asset catalog, using fallback:', error);
    }
  };

  const fetchAvailableFiles = async () => {
    try {
      const response = await fetch(`${API_URL}/configs`);
      const data = await response.json();
      setAvailableFiles(data.files || []);
    } catch (error) {
      console.error('Failed to fetch available files:', error);
    }
  };

  const onNodesChange = (changes: Parameters<OnNodesChange>[0]) => {
    setNodes((prev) => applyNodeChanges(changes, prev));
  };

  const onEdgesChange = (changes: Parameters<OnEdgesChange>[0]) => {
    setEdges((prev) => applyEdgeChanges(changes, prev));
  };

  const getPortMedium = (nodeId: string, handleId: string, direction: 'source' | 'target'): Medium | null => {
    const node = nodes.find((entry) => entry.id === nodeId);
    if (!node) return null;
    return getPortMediumFromNode(node, handleId, direction);
  };

  const isValidConnection = (connection: Connection): boolean => {
    if (!connection.source || !connection.target || !connection.sourceHandle || !connection.targetHandle) {
      return false;
    }

    const sourceNode = nodes.find((node) => node.id === connection.source);
    const targetNode = nodes.find((node) => node.id === connection.target);
    if (!sourceNode || !targetNode) return false;

    const sourceIsPipe = isPipeNode(sourceNode);
    const targetIsPipe = isPipeNode(targetNode);
    if (sourceIsPipe && targetIsPipe) return false;

    if (!sourceIsPipe) {
      const sourceAlreadyConnected = edges.some(
        (edge) => edge.source === connection.source && String(edge.sourceHandle ?? '') === connection.sourceHandle
      );
      if (sourceAlreadyConnected) return false;
    }

    if (!targetIsPipe) {
      const targetAlreadyConnected = edges.some(
        (edge) => edge.target === connection.target && String(edge.targetHandle ?? '') === connection.targetHandle
      );
      if (targetAlreadyConnected) return false;
    }

    const sourceMedium = getPortMedium(connection.source, connection.sourceHandle, 'source');
    const targetMedium = getPortMedium(connection.target, connection.targetHandle, 'target');
    return sourceMedium !== null && sourceMedium === targetMedium;
  };

  const onConnect = (connection: Connection) => {
    if (!isValidConnection(connection)) return;

    const sourceNode = nodes.find((node) => node.id === connection.source);
    const targetNode = nodes.find((node) => node.id === connection.target);
    if (!sourceNode || !targetNode) return;

    const sourcePort = String(connection.sourceHandle ?? '');
    const targetPort = String(connection.targetHandle ?? '');
    const medium = normalizeMedium(getPortMedium(connection.source ?? '', sourcePort, 'source') ?? 'electric');

    // Connecting asset -> asset creates an intermediate pipe node automatically.
    if (!isPipeNode(sourceNode) && !isPipeNode(targetNode)) {
      const newPipeId = `pipe_${uuidv4().slice(0, 8)}`;
      const pipeNode = buildPipeNode(
        newPipeId,
        (sourceNode.position.x + targetNode.position.x) / 2,
        (sourceNode.position.y + targetNode.position.y) / 2,
        medium,
        1,
        1
      );

      const edgeToPipe: Edge = {
        id: `conn_${uuidv4().slice(0, 8)}`,
        source: sourceNode.id,
        target: newPipeId,
        sourceHandle: sourcePort,
        targetHandle: 'in_1',
        type: 'routed',
        markerEnd: edgeMarker(medium),
        data: { medium },
        style: edgeStyle(medium),
      };

      const edgeFromPipe: Edge = {
        id: `conn_${uuidv4().slice(0, 8)}`,
        source: newPipeId,
        target: targetNode.id,
        sourceHandle: 'out_1',
        targetHandle: targetPort,
        type: 'routed',
        markerEnd: edgeMarker(medium),
        data: { medium },
        style: edgeStyle(medium),
      };

      setNodes((prev) => [...prev, pipeNode]);
      setEdges((prev) => addEdge(edgeFromPipe, addEdge(edgeToPipe, prev)));
      return;
    }

    const id = `conn_${uuidv4().slice(0, 8)}`;

    setEdges((prev) =>
      addEdge(
        {
          ...connection,
          id,
          type: 'routed',
          markerEnd: edgeMarker(medium),
          data: {
            medium,
          },
          style: edgeStyle(medium),
        },
        prev
      )
    );
  };

  const addAsset = () => {
    const meta = assetCatalog[assetTypeToAdd];
    if (!meta) return;

    const newId = `${assetTypeToAdd}_${uuidv4().slice(0, 8)}`;
    const preset = Object.keys(meta.presets)[0] ?? 'Default';
    const params = meta.presets[preset] ?? {};

    setNodes((prev) => [
      ...prev,
      buildAssetNode(
        newId,
        180,
        180,
        assetTypeToAdd,
        `${meta.displayName} ${prev.length + 1}`,
        preset,
        { ...params },
        meta.color,
        assetCatalog
      ),
    ]);
  };

  const deleteSelected = () => {
    if (selectedNodeId) {
      setNodes((prev) => prev.filter((node) => node.id !== selectedNodeId));
      setEdges((prev) => prev.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
      setSelectedNodeId(null);
      return;
    }

    if (selectedEdgeId) {
      setEdges((prev) => prev.filter((edge) => edge.id !== selectedEdgeId));
      setSelectedEdgeId(null);
    }
  };

  const updateSelectedAsset = (patch: Partial<ConfigAsset>) => {
    if (!selectedNodeId) return;
    setNodes((prev) =>
      prev.map((node) => {
        if (node.id !== selectedNodeId || node.data.kind !== 'asset') return node;

        const data = { ...node.data };
        if (patch.name !== undefined) data.name = patch.name;
        if (patch.preset !== undefined) data.preset = patch.preset;
        if (patch.color !== undefined) data.color = patch.color;
        if (patch.params !== undefined) data.params = patch.params;
        data.ports = getPortsForType(String(data.assetType), assetCatalog);
        const maxPortCount = Math.max(data.ports.in.length, data.ports.out.length, 1);

        return {
          ...node,
          data,
          style: assetNodeStyle(String(data.color ?? '#cccccc'), data.name, maxPortCount),
        };
      })
    );
  };

  const updateSelectedAssetParam = (key: string, value: string | number | boolean) => {
    if (!selectedNode || selectedNode.data.kind !== 'asset') return;
    const params = { ...(selectedNode.data.params as AssetParams), [key]: value };
    updateSelectedAsset({ params });
  };

  const saveFile = async () => {
    try {
      const text = serializeConfigYaml(nodes, edges);
      const response = await fetch(`${API_URL}/configs/${currentFileName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      });
      if (!response.ok) throw new Error('Failed to save file');
    } catch (error) {
      console.error('Error saving file:', error);
    }
  };

  const applyParsedConfig = (text: string) => {
    const parsed = parseConfigYaml(text);
    const graph = buildGraphFromConfig(parsed.assets, parsed.pipes, assetCatalog);
    setNodes(graph.nodes);
    setEdges(graph.edges);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
  };

  const loadYaml = async (file: File) => {
    const text = await file.text();
    applyParsedConfig(text);
  };

  const copyFile = async () => {
    const newFileName = `${currentFileName}_copy`;
    try {
      const text = serializeConfigYaml(nodes, edges);
      const response = await fetch(`${API_URL}/configs/${newFileName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      });
      if (!response.ok) throw new Error('Failed to copy file');
      await fetchAvailableFiles();
    } catch (error) {
      console.error('Error copying file:', error);
    }
  };

  const newFile = async () => {
    await saveFile();
    setNodes(defaultNodes(assetCatalog));
    setEdges([]);
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setCurrentFileName('new_file');
    setFileNameInput('new_file');
  };

  const renameFile = async () => {
    if (fileNameInput === currentFileName || fileNameInput.trim() === '') {
      return;
    }

    try {
      const text = serializeConfigYaml(nodes, edges);
      const response = await fetch(`${API_URL}/configs/${fileNameInput}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      });
      if (!response.ok) throw new Error('Failed to save with new name');

      const deleteResponse = await fetch(`${API_URL}/configs/${currentFileName}`, {
        method: 'DELETE',
      });
      if (!deleteResponse.ok) throw new Error('Failed to delete old file');

      await fetchAvailableFiles();
      setCurrentFileName(fileNameInput);
    } catch (error) {
      console.error('Error renaming file:', error);
    }
  };

  const saveOrRename = () => {
    if (fileNameInput === currentFileName || fileNameInput.trim() === '') {
      void saveFile();
    } else {
      void renameFile();
    }
  };

  const loadFile = async (fileName: string) => {
    await saveFile();

    try {
      const response = await fetch(`${API_URL}/configs/${fileName}`);
      if (!response.ok) throw new Error('File not found');

      const data = await response.json();
      applyParsedConfig(String(data.content ?? ''));
      setCurrentFileName(fileName);
      setFileNameInput(fileName);
    } catch (error) {
      console.error('Error loading file:', error);
    }
  };

  const assetTypeEntries = Object.entries(assetCatalog);

  // Filter nodes and edges based on active medium
  const visibleNodes = useMemo(() => {
    return nodes.filter((node) => {
      if (node.data.kind === 'pipe') {
        return normalizeMedium(node.data.medium) === activeMedium;
      }
      // Asset nodes are always visible, just filtering their ports happens during render
      return true;
    });
  }, [nodes, activeMedium]);

  const visibleEdges = useMemo(() => {
    return edges.filter((edge) => {
      const medium = normalizeMedium(edge.data?.medium ?? 'electric');
      return medium === activeMedium;
    });
  }, [edges, activeMedium]);

  const nodeTypes = useMemo(
    () => ({
      asset: (props: any) => <AssetNode {...props} activeMedium={activeMedium} />,
      pipe: (props: any) => <PipeNode {...props} activeMedium={activeMedium} />,
    }),
    [activeMedium]
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <h1>SolarSim</h1>

        <section className="card">
          <h2>File</h2>

          <div className="file-row">
            <button onClick={newFile}>New File</button>
            <button onClick={copyFile}>Clone File</button>
          </div>

          <div className="file-row">
            <input
              type="text"
              value={fileNameInput}
              onChange={(event) => setFileNameInput(event.target.value)}
              placeholder="File name"
            />
            <button onClick={saveOrRename} className="icon-button" title="Save or rename">
              {fileNameInput === currentFileName ? 'S' : 'R'}
            </button>
          </div>

          <select
            value={selectedLoadFile}
            onChange={(event) => {
              const fileName = event.target.value;
              if (fileName) {
                void loadFile(fileName);
                setSelectedLoadFile('');
              }
            }}
          >
            <option value="">Load File</option>
            {availableFiles.map((file) => (
              <option key={file} value={file}>
                {file}
              </option>
            ))}
          </select>

          <input
            ref={fileInputRef}
            type="file"
            accept=".yaml,.yml"
            className="hidden-input"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                void loadYaml(file);
              }
              event.currentTarget.value = '';
            }}
          />
        </section>

        <section className="card">
          <h2>Add Asset</h2>
          <select value={assetTypeToAdd} onChange={(event) => setAssetTypeToAdd(event.target.value)}>
            {assetTypeEntries.map(([assetType, meta]) => (
              <option key={assetType} value={assetType}>
                {meta.displayName}
              </option>
            ))}
          </select>
          <button onClick={addAsset}>Add Asset</button>
        </section>

        <section className="card">
          <h2>Selection</h2>
          <button onClick={deleteSelected}>Delete Selected</button>
          <p className="hint">Connecting one asset to another creates a pipe node automatically.</p>
        </section>

        {selectedNode && selectedNode.data.kind === 'asset' && (
          <section className="card">
            <h2>Asset</h2>
            <label>Name</label>
            <input value={selectedNode.data.name} onChange={(event) => updateSelectedAsset({ name: event.target.value })} />

            <label>Color</label>
            <input
              type="color"
              value={selectedNode.data.color}
              onChange={(event) => updateSelectedAsset({ color: event.target.value })}
            />

            {Object.entries(selectedNode.data.params).map(([key, value]) => (
              <div key={key}>
                <label>{key}</label>
                <input
                  value={String(value)}
                  onChange={(event) => {
                    const current = value;
                    if (typeof current === 'number') {
                      updateSelectedAssetParam(key, Number(event.target.value));
                      return;
                    }
                    if (typeof current === 'boolean') {
                      updateSelectedAssetParam(key, event.target.value === 'true');
                      return;
                    }
                    updateSelectedAssetParam(key, event.target.value);
                  }}
                />
              </div>
            ))}
          </section>
        )}

      </aside>

      <main className="canvas-pane">
        <div className="medium-tabs">
          {(['electric', 'thermal', 'monetary', 'data'] as const).map((medium) => (
            <button
              key={medium}
              className={`tab-button ${activeMedium === medium ? 'active' : ''}`}
              onClick={() => setActiveMedium(medium)}
              style={{
                backgroundColor: activeMedium === medium ? mediumColor(medium) : '#e5e7eb',
                color: activeMedium === medium ? '#ffffff' : '#374151',
                border: `2px solid ${mediumColor(medium)}`,
              }}
            >
              {medium.charAt(0).toUpperCase() + medium.slice(1)}
            </button>
          ))}
        </div>
        <ReactFlow
          nodes={visibleNodes}
          edges={visibleEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          isValidConnection={isValidConnection}
          nodeTypes={nodeTypes}
          edgeTypes={{ routed: RoutedEdge }}
          onSelectionChange={({ nodes: selectedNodes, edges: selectedEdges }) => {
            setSelectedNodeId(selectedNodes[0]?.id ?? null);
            setSelectedEdgeId(selectedEdges[0]?.id ?? null);
          }}
          deleteKeyCode={['Backspace', 'Delete']}
          fitView
          minZoom={0.05}
          panOnDrag
          zoomOnScroll
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#d1d5db" gap={24} />
          <MiniMap zoomable pannable />
          <Controls />
        </ReactFlow>
      </main>
    </div>
  );
}
