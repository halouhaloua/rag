import type { Ref } from 'vue';

import type { GraphData, GraphLink } from '#/api/core/rag';

import { onUnmounted, ref, shallowRef } from 'vue';

import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';

import {
  computeNodeSizes,
  computeNoverlapsLayout,
  computeStaticForceLayout,
} from '#/composables/useGraphLayout';
import { entityColorService } from '#/services/entityColorService';

echarts.use([GraphChart, TooltipComponent, TitleComponent, CanvasRenderer]);

export function useGraphChart(
  containerRef: Ref<HTMLElement | null>,
  emit?: (event: string, ...args: any[]) => void,
) {
  const chartInstance = shallowRef<echarts.ECharts | null>(null);
  const selectedType = ref<null | string>(null);
  const currentScheme = ref<string>('vibrant');

  let currentGraphData: GraphData | null = null;
  let currentLayout: string = 'force';
  const nodeDraggedPositions = new Map<string, { x: number; y: number }>();

  function getSeriesBase() {
    return {
      type: 'graph' as const,
      roam: true,
      symbol: 'circle',
      draggable: true,
      focusNodeAdjacency: true,
      label: {
        show: true,
        position: 'right',
        color: '#1a1a2e',
        fontSize: 11,
        formatter: (p: any) => {
          const name = p.data?.name || '';
          return name.length > 15 ? `${name.slice(0, 15)}...` : name;
        },
      },
      lineStyle: {
        opacity: 0.6,
        curveness: 0.1,
        color: '#a0aec0',
      },
      edgeLabel: {
        show: true,
        color: '#718096',
        fontSize: 10,
        formatter: (p: any) => {
          const name = p.data?.name || '';
          return name.length > 10 ? `${name.slice(0, 10)}...` : name;
        },
      },
      emphasis: {
        focus: 'adjacency',
        lineStyle: { width: 3, opacity: 1 },
        itemStyle: {
          shadowBlur: 20,
          shadowColor: 'rgba(0, 0, 0, 0.3)',
        },
      },
      itemStyle: { borderWidth: 2, borderColor: '#fff' },
    };
  }

  function initChart() {
    if (!containerRef.value) return;
    if (chartInstance.value) {
      chartInstance.value.dispose();
    }

    chartInstance.value = echarts.init(containerRef.value);

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#1a1a2e' },
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `<strong>${params.data.name}</strong><br/>类型: ${params.data.category}`;
          }
          if (params.dataType === 'edge') {
            return `${params.data.source} → ${params.data.target}<br/>关系: ${params.data.name}`;
          }
          return '';
        },
      },
      legend: { show: false },
      series: [
        {
          type: 'graph' as const,
          layout: 'force',
          data: [],
          links: [],
          categories: [],
          roam: true,
          symbol: 'circle',
          draggable: true,
          focusNodeAdjacency: true,
          label: {
            show: true,
            position: 'right',
            color: '#1a1a2e',
            fontSize: 11,
            formatter: (p: any) => {
              const name = p.data?.name || '';
              return name.length > 15 ? `${name.slice(0, 15)}...` : name;
            },
          },
          force: {
            repulsion: 800,
            gravity: 0.1,
            edgeLength: [100, 200],
            layoutAnimation: true,
          },
          lineStyle: {
            opacity: 0.6,
            curveness: 0.1,
            color: '#a0aec0',
          },
          edgeLabel: {
            show: true,
            color: '#718096',
            fontSize: 10,
            formatter: (p: any) => {
              const name = p.data?.name || '';
              return name.length > 10 ? `${name.slice(0, 10)}...` : name;
            },
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 3, opacity: 1 },
            itemStyle: {
              shadowBlur: 20,
              shadowColor: 'rgba(0, 0, 0, 0.3)',
            },
          },
          itemStyle: { borderWidth: 2, borderColor: '#fff' },
        },
      ],
    };

    chartInstance.value.setOption(option);

    chartInstance.value.on('click', (params: any) => {
      if (params.dataType === 'node') {
        emit?.('node-click', params.data);
      } else if (params.dataType === 'edge') {
        emit?.('edge-click', params.data);
      } else if (!params.data) {
        emit?.('background-click');
      }
    });

    chartInstance.value.on('dragend', (params: any) => {
      if (params.dataType === 'node' && params.data && params.data.id) {
        nodeDraggedPositions.set(params.data.id, {
          x: params.data.x,
          y: params.data.y,
        });
      }
    });
  }

  function getEChartsPositions(): Record<string, { x: number; y: number }> {
    if (!chartInstance.value) return {};
    try {
      const option = chartInstance.value.getOption() as any;
      const data = (option.series?.[0]?.data ?? []) as any[];
      const positions: Record<string, { x: number; y: number }> = {};
      for (const node of data) {
        if (node.id && node.x !== null && node.y !== null) {
          positions[node.id] = { x: node.x, y: node.y };
        }
      }
      return positions;
    } catch {
      return {};
    }
  }

  function prepareChartData(data: GraphData) {
    let { nodes, links, categories } = data;

    const allTypes = [...new Set(nodes.map((n) => n.category))];
    entityColorService.updateEntityTypes(allTypes);

    if (selectedType.value) {
      const filteredNodesList = nodes.filter(
        (node) => node.category === selectedType.value,
      );
      const filteredNodeIds = new Set(filteredNodesList.map((n) => n.id));
      const filteredLinks = links.filter(
        (link) =>
          filteredNodeIds.has(link.source) && filteredNodeIds.has(link.target),
      );
      nodes = filteredNodesList;
      links = filteredLinks;
    }

    const sizeMap = computeNodeSizes(nodes, links);

    const coloredNodes = nodes.map((node) => ({
      ...node,
      symbolSize: sizeMap[node.id]?.symbolSize ?? 10,
      itemStyle: { color: entityColorService.getColor(node.category) },
    }));

    const coloredCategories = categories.map((cat) => ({
      ...cat,
      itemStyle: { color: entityColorService.getColor(cat.name) },
    }));

    return { nodes: coloredNodes, links, categories: coloredCategories };
  }

  function updateChart(data: GraphData, schemeName?: string) {
    if (!chartInstance.value) {
      initChart();
    }
    if (!chartInstance.value) return;

    currentGraphData = data;
    if (schemeName) {
      entityColorService.setSchemeByName(schemeName);
      currentScheme.value = schemeName;
    }

    const prepared = prepareChartData(data);
    applyLayout(currentLayout, prepared);
  }

  function applyLayout(
    layoutType: string,
    prepared?: {
      categories: any[];
      links: GraphLink[];
      nodes: any[];
    },
  ) {
    if (!chartInstance.value) return;

    const graphData = currentGraphData;
    if (!graphData) return;
    const data = prepared || prepareChartData(graphData);
    if (!data) return;

    currentLayout = layoutType;

    const chartWidth = chartInstance.value.getWidth() || 800;
    const chartHeight = chartInstance.value.getHeight() || 600;

    if (layoutType === 'force' || layoutType === 'force-atlas-2') {
      chartInstance.value.setOption({
        series: [
          {
            ...getSeriesBase(),
            layout: 'force',
            force: {
              repulsion: 800,
              gravity: 0.1,
              edgeLength: [100, 200],
              layoutAnimation: true,
            },
            data: data.nodes,
            links: data.links,
            categories: data.categories,
          },
        ],
      });
      return;
    }

    if (layoutType === 'circular') {
      chartInstance.value.setOption({
        series: [
          {
            ...getSeriesBase(),
            layout: 'circular',
            circular: { rotateLabel: true },
            data: data.nodes,
            links: data.links,
            categories: data.categories,
          },
        ],
      });
      return;
    }

    const positions = getEChartsPositions();
    for (const [id, pos] of nodeDraggedPositions) {
      positions[id] = pos;
    }

    let computed: Record<string, { x: number; y: number }> = {};

    if (layoutType === 'noverlaps') {
      const nodesWithSize = (currentGraphData?.nodes || []).map((n) => ({
        id: n.id,
        symbolSize:
          data.nodes.find((dn: any) => dn.id === n.id)?.symbolSize ?? 20,
      }));
      computed = computeNoverlapsLayout(nodesWithSize, positions, {
        width: chartWidth,
        height: chartHeight,
      });
    } else if (layoutType === 'static-force') {
      const storeNodes = currentGraphData?.nodes ?? [];
      const storeLinks = currentGraphData?.links ?? [];
      computed = computeStaticForceLayout(storeNodes, storeLinks, {
        width: chartWidth,
        height: chartHeight,
      });
    }

    const positionedNodes = data.nodes.map((n: any) => ({
      ...n,
      x: computed[n.id]?.x ?? Math.random() * chartWidth,
      y: computed[n.id]?.y ?? Math.random() * chartHeight,
      fixed: true,
    }));

    chartInstance.value.setOption({
      series: [
        {
          ...getSeriesBase(),
          layout: 'none',
          data: positionedNodes,
          links: data.links,
          categories: data.categories,
        },
      ],
    });
  }

  function highlightNode(nodeName: string) {
    if (!chartInstance.value) return;
    chartInstance.value.dispatchAction({ type: 'downplay' });
    chartInstance.value.dispatchAction({
      type: 'highlight',
      seriesIndex: 0,
      name: nodeName,
    });
    chartInstance.value.dispatchAction({
      type: 'showTip',
      seriesIndex: 0,
      name: nodeName,
    });
  }

  function setColorScheme(schemeName: string) {
    currentScheme.value = schemeName;
    entityColorService.setSchemeByName(schemeName);
    if (currentGraphData) {
      updateChart(currentGraphData);
    }
  }

  function filterByCategory(type: null | string) {
    selectedType.value = type;
    if (currentGraphData) {
      updateChart(currentGraphData);
    }
  }

  function resetView() {
    if (!chartInstance.value || !currentGraphData) return;
    chartInstance.value.dispatchAction({ type: 'restore' });
    nodeDraggedPositions.clear();
    updateChart(currentGraphData);
  }

  function handleResize() {
    chartInstance.value?.resize();
  }

  function dispose() {
    chartInstance.value?.dispose();
    chartInstance.value = null;
  }

  onUnmounted(() => {
    dispose();
  });

  return {
    chartInstance,
    selectedType,
    currentScheme,
    initChart,
    updateChart,
    applyLayout,
    setColorScheme,
    filterByCategory,
    resetView,
    handleResize,
    highlightNode,
    dispose,
  };
}
