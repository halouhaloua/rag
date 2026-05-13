<script lang="ts" setup>
import type { GraphNode } from '#/api/core/rag';

import { computed } from 'vue';

import { entityColorService } from '#/services/entityColorService';

interface LegendItem {
  name: string;
  count: number;
  percentage: number;
  color: string;
}

const props = defineProps<{
  colorVersion: number;
  edges?: number;
  nodes: GraphNode[];
  selectedType: null | string;
  statsNodes?: number;
}>();

defineEmits<{
  clearFilter: [];
  typeClick: [type: string];
}>();

const entityTypeDistribution = computed<LegendItem[]>(() => {
  if (props.nodes.length === 0) return [];
  void props.colorVersion;

  const total = props.nodes.length;
  const typeCount: Record<string, number> = {};

  props.nodes.forEach((node) => {
    typeCount[node.category] = (typeCount[node.category] || 0) + 1;
  });

  return Object.entries(typeCount)
    .map(([name, count]) => ({
      name,
      count,
      percentage: total > 0 ? Math.round((count / total) * 100) : 0,
      color: entityColorService.getColor(name),
    }))
    .sort((a, b) => b.count - a.count);
});

const totalNodes = computed(() => props.nodes.length);
</script>

<template>
  <div class="entity-legend">
    <div class="legend-header">
      <h5>ENTITY TYPES</h5>
      <span class="total-count">
        节点: {{ statsNodes ?? totalNodes }} | 边: {{ edges ?? 0 }}
      </span>
    </div>
    <div class="legend-content">
      <div
        v-for="(item, index) in entityTypeDistribution"
        :key="index"
        class="legend-item"
        :class="[{ active: selectedType === item.name }]"
        @click="$emit('typeClick', item.name)"
      >
        <div class="legend-left">
          <span class="legend-dot" :style="{ background: item.color }"></span>
          <span class="legend-label">{{ item.name }}</span>
        </div>
        <div class="legend-right">
          <span class="legend-count">{{ item.count }}</span>
          <span class="legend-percent">{{ item.percentage }}%</span>
        </div>
      </div>
    </div>
    <div v-if="selectedType" class="legend-footer">
      <el-button
        size="small"
        type="primary"
        plain
        @click="$emit('clearFilter')"
      >
        清除筛选
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.entity-legend {
  position: absolute;
  right: 20px;
  bottom: 20px;
  z-index: 100;
  width: 220px;
  background: rgb(255 255 255 / 95%);
  border: 1px solid rgb(226 232 240 / 80%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgb(0 0 0 / 10%);
  backdrop-filter: blur(10px);
}

.legend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.legend-header h5 {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.5px;
}

.legend-header .total-count {
  font-size: 12px;
  color: #94a3b8;
}

.legend-content {
  max-height: 200px;
  padding: 8px;
  overflow-y: auto;
}

.legend-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
}

.legend-item:hover {
  background: var(--el-bg-color-page);
}

.legend-item.active {
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary);
}

.legend-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-label {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a2e;
}

.legend-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.legend-count {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.legend-percent {
  width: 35px;
  font-size: 11px;
  color: #94a3b8;
  text-align: right;
}

.legend-footer {
  display: flex;
  justify-content: center;
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
}
</style>
