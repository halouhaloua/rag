<script lang="ts" setup>
import type { GraphData, GraphNode } from '#/api/core/rag';
import type { LayoutType } from '#/composables/useGraphLayout';

import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import { useGraphChart } from '#/composables/useGraphChart';

import EntityLegend from './EntityLegend.vue';
import NodeDetailsPanel from './NodeDetailsPanel.vue';
import NodeSearchBar from './NodeSearchBar.vue';

const props = defineProps<{
  graphData: GraphData | null;
  layout?: LayoutType;
  loading?: boolean;
}>();

const emit = defineEmits<{
  nodeClick: [node: GraphNode];
}>();

const containerRef = ref<HTMLElement | null>(null);
const selectedNode = ref<GraphNode | null>(null);
const colorVersion = ref(0);

const searchQuery = ref('');
const isSearchFocused = ref(false);
const showSearchResults = ref(false);
const selectedResultIndex = ref(0);

const filteredNodes = computed(() => {
  if (!searchQuery.value.trim()) return [];
  const query = searchQuery.value.toLowerCase();
  return (props.graphData?.nodes || [])
    .filter(
      (node) =>
        node.name.toLowerCase().includes(query) ||
        node.category.toLowerCase().includes(query),
    )
    .slice(0, 10);
});

function onChartEvent(eventType: string, data?: GraphNode) {
  if (eventType === 'node-click') {
    selectedNode.value = data as GraphNode;
    emit('nodeClick', data as GraphNode);
  }
}

const chartEmit = (event: string, ...args: any[]) =>
  onChartEvent(event, ...args);

const {
  selectedType,
  updateChart,
  applyLayout,
  filterByCategory,
  resetView,
  handleResize,
  highlightNode,
} = useGraphChart(containerRef, chartEmit);

function selectAndLocateNode(node: GraphNode) {
  selectedNode.value = node;
  highlightNode(node.name);
  emit('nodeClick', node);
}

function searchAndLocate() {
  if (filteredNodes.value.length > 0 && selectedResultIndex.value >= 0) {
    const node = filteredNodes.value[selectedResultIndex.value];
    if (node) {
      selectAndLocateNode(node);
      searchQuery.value = node.name;
      showSearchResults.value = false;
    }
  }
}

function filterByType(type: string) {
  filterByCategory(selectedType.value === type ? null : type);
}

function clearFilter() {
  filterByCategory(null);
}

watch(
  () => props.graphData,
  (data) => {
    if (data && data.nodes.length > 0) {
      colorVersion.value++;
      updateChart(data);
    }
  },
  { deep: true },
);

watch(
  () => props.layout,
  (newLayout) => {
    if (newLayout && props.graphData) {
      applyLayout(newLayout);
    }
  },
);

onMounted(() => {
  window.addEventListener('resize', handleResize);
  if (props.graphData && props.graphData.nodes.length > 0) {
    colorVersion.value++;
    updateChart(props.graphData);
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});

defineExpose({
  resetView,
  updateColors: () => {
    colorVersion.value++;
    if (props.graphData) updateChart(props.graphData);
  },
  applyLayout: (layout: LayoutType) => applyLayout(layout),
});
</script>

<template>
  <div class="graph-visualization">
    <div class="graph-main">
      <div ref="containerRef" class="chart-container"></div>

      <div v-if="!graphData" class="empty-hint">
        请先选择知识库和已构建图谱的文件
      </div>

      <div class="top-left-panel">
        <slot></slot>
        <NodeSearchBar
          v-model:search-query="searchQuery"
          v-model:is-search-focused="isSearchFocused"
          v-model:show-search-results="showSearchResults"
          v-model:selected-result-index="selectedResultIndex"
          :filtered-nodes="filteredNodes"
          @node-select="selectAndLocateNode"
          @search-and-locate="searchAndLocate"
        />
      </div>

      <NodeDetailsPanel :node="selectedNode" @close="selectedNode = null" />

      <EntityLegend
        :nodes="graphData?.nodes || []"
        :selected-type="selectedType"
        :color-version="colorVersion"
        :stats-nodes="graphData?.stats.total_nodes ?? 0"
        :edges="graphData?.stats.total_edges ?? 0"
        @type-click="filterByType"
        @clear-filter="clearFilter"
      />
    </div>
  </div>
</template>

<style scoped>
.graph-visualization {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.graph-main {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.chart-container {
  width: 100%;
  height: 100%;
}

.empty-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  z-index: 50;
  font-size: 16px;
  color: var(--el-text-color-secondary);
  transform: translate(-50%, -50%);
}

.top-left-panel {
  position: absolute;
  top: 12px;
  left: 16px;
  z-index: 100;
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
