import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';

export type LayoutType = 'circular' | 'static-force' | 'noverlaps' | 'force' | 'force-atlas-2';

export const LAYOUT_OPTIONS: { key: LayoutType; label: string }[] = [
  { key: 'force', label: '力导向' },
  { key: 'circular', label: '环形' },
  { key: 'static-force', label: '静态力导向' },
  { key: 'noverlaps', label: '防重叠' },
  { key: 'force-atlas-2', label: 'Force Atlas 2' },
];

export function computeNodeSizes(
  nodes: { id: string }[],
  links: { source: string; target: string }[],
  minSize = 5,
  maxSize = 20,
): Record<string, { degree: number; symbolSize: number }> {
  const degreeMap = new Map<string, number>();
  for (const node of nodes) degreeMap.set(node.id, 0);
  for (const link of links) {
    degreeMap.set(link.source, (degreeMap.get(link.source) || 0) + 1);
    degreeMap.set(link.target, (degreeMap.get(link.target) || 0) + 1);
  }
  let minDegree = Number.MAX_SAFE_INTEGER;
  let maxDegree = 0;
  for (const degree of degreeMap.values()) {
    minDegree = Math.min(minDegree, degree);
    maxDegree = Math.max(maxDegree, degree);
  }
  const range = maxDegree - minDegree;
  const scale = maxSize - minSize;
  const result: Record<string, { degree: number; symbolSize: number }> = {};
  if (range > 0) {
    for (const [id, degree] of degreeMap) {
      const symbolSize = Math.round(minSize + scale * Math.sqrt((degree - minDegree) / range));
      result[id] = { degree, symbolSize };
    }
  } else {
    const midSize = Math.round((minSize + maxSize) / 2);
    for (const [id, degree] of degreeMap) {
      result[id] = { degree, symbolSize: midSize };
    }
  }
  return result;
}

export function computeStaticForceLayout(
  nodes: { id: string }[],
  links: { source: string; target: string }[],
  options?: { width?: number; height?: number; iterations?: number },
): Record<string, { x: number; y: number }> {
  const width = options?.width ?? 800;
  const height = options?.height ?? 600;
  const iterations = options?.iterations ?? 400;
  const centerX = width / 2;
  const centerY = height / 2;

  const simNodes = nodes.map((n) => ({
    id: n.id,
    x: centerX + (Math.random() - 0.5) * width * 0.3,
    y: centerY + (Math.random() - 0.5) * height * 0.3,
  }));
  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
  const simLinks = links
    .filter((l) => nodeMap.has(l.source) && nodeMap.has(l.target))
    .map((l) => ({ source: nodeMap.get(l.source)!, target: nodeMap.get(l.target)! }));

  const simulation = forceSimulation(simNodes as any)
    .force('link', forceLink(simLinks).distance(200).strength(0.2))
    .force('charge', forceManyBody().strength(-3000))
    .force('center', forceCenter(centerX, centerY).strength(0.05))
    .alphaDecay(0.01)
    .alpha(1)
    .stop();

  for (let i = 0; i < iterations; i++) simulation.tick();

  const positions: Record<string, { x: number; y: number }> = {};
  for (const d of simNodes) positions[d.id] = { x: d.x, y: d.y };
  return positions;
}

export function computeNoverlapsLayout(
  nodes: { id: string; symbolSize?: number }[],
  initialPositions?: Record<string, { x: number; y: number }>,
  options?: { width?: number; height?: number; iterations?: number },
): Record<string, { x: number; y: number }> {
  const width = options?.width ?? 800;
  const height = options?.height ?? 600;
  const iterations = options?.iterations ?? 200;
  const centerX = width / 2;
  const centerY = height / 2;

  const simNodes = nodes.map((node) => {
    const initPos = initialPositions?.[node.id];
    const radius = ((node.symbolSize ?? 20) / 2) + 4;
    return {
      id: node.id,
      x: initPos?.x ?? centerX + (Math.random() - 0.5) * width * 0.3,
      y: initPos?.y ?? centerY + (Math.random() - 0.5) * height * 0.3,
      r: radius,
    };
  });

  const simulation = forceSimulation(simNodes as any)
    .force('center', forceCenter(centerX, centerY).strength(0.05))
    .force('collide', forceCollide((d: any) => d.r).strength(0.8))
    .alphaDecay(0.04)
    .alpha(0.6)
    .stop();

  for (let i = 0; i < iterations; i++) simulation.tick();

  const positions: Record<string, { x: number; y: number }> = {};
  for (const d of simNodes) positions[d.id] = { x: d.x, y: d.y };
  return positions;
}

export function computeForceAtlas2Layout(
  nodes: { id: string }[],
  links: { source: string; target: string }[],
  options?: { width?: number; height?: number; iterations?: number },
): Record<string, { x: number; y: number }> {
  const width = options?.width ?? 800;
  const height = options?.height ?? 600;
  const iterations = options?.iterations ?? 500;
  const centerX = width / 2;
  const centerY = height / 2;

  const degrees: Record<string, number> = {};
  for (const n of nodes) degrees[n.id] = 0;
  for (const l of links) {
    degrees[l.source] = (degrees[l.source] || 0) + 1;
    degrees[l.target] = (degrees[l.target] || 0) + 1;
  }

  const simNodes = nodes.map((n) => ({
    id: n.id,
    x: centerX + (Math.random() - 0.5) * width * 0.3,
    y: centerY + (Math.random() - 0.5) * height * 0.3,
  }));
  const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
  const simLinks = links
    .filter((l) => nodeMap.has(l.source) && nodeMap.has(l.target))
    .map((l) => ({
      source: nodeMap.get(l.source)!,
      target: nodeMap.get(l.target)!,
      distance: 1 / (Math.log((degrees[l.source] || 1) + (degrees[l.target] || 1)) + 1) * 200 + 30,
    }));

  const simulation = forceSimulation(simNodes as any)
    .force('link', forceLink(simLinks).id((d: any) => d.id).distance((l: any) => l.distance))
    .force('charge', forceManyBody().strength(-500))
    .force('center', forceCenter(centerX, centerY).strength(0.05))
    .alphaDecay(0.02)
    .alpha(1)
    .stop();

  for (let i = 0; i < iterations; i++) simulation.tick();

  const positions: Record<string, { x: number; y: number }> = {};
  for (const d of simNodes) positions[d.id] = { x: d.x, y: d.y };
  return positions;
}
