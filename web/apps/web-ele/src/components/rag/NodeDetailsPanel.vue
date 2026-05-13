<script lang="ts" setup>
import type { GraphNode } from '#/api/core/rag';

import { Close } from '@element-plus/icons-vue';

defineProps<{
  node: GraphNode | null;
}>();

defineEmits<{
  close: [];
}>();

function getNodeTypeTag(category: string) {
  const tagMap: Record<string, string> = {
    Company: 'success',
    Person: 'warning',
    Organization: 'info',
    Entity: '',
  };
  return tagMap[category] || '';
}

function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}
</script>

<template>
  <div v-if="node" class="node-details-panel">
    <div class="panel-header">
      <h4>Node Details</h4>
      <el-tag :type="getNodeTypeTag(node.category)">{{ node.category }}</el-tag>
      <el-button
        class="close-btn"
        :icon="Close"
        circle
        size="small"
        @click="$emit('close')"
      />
    </div>
    <div class="panel-content">
      <div class="detail-item">
        <span class="detail-label">Name:</span>
        <span class="detail-value">{{ node.name }}</span>
      </div>
      <div class="detail-item">
        <span class="detail-label">UUID:</span>
        <span class="detail-value uuid">{{ node.id }}</span>
      </div>
      <div v-if="node.properties" class="detail-section">
        <h5>Properties:</h5>
        <div
          v-for="(value, key) in node.properties"
          :key="key"
          class="detail-item"
        >
          <span class="detail-label">{{ key }}:</span>
          <div v-if="isArray(value)" class="detail-value detail-value-array">
            <el-tag
              v-for="(item, i) in value"
              :key="i"
              class="array-tag"
              size="small"
              effect="plain"
            >
              {{ item }}
            </el-tag>
          </div>
          <span v-else class="detail-value">{{ value }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.node-details-panel {
  position: absolute;
  top: 80px;
  right: 20px;
  z-index: 100;
  width: 300px;
  background: rgb(255 255 255 / 95%);
  border: 1px solid rgb(226 232 240 / 80%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgb(0 0 0 / 10%);
  backdrop-filter: blur(10px);
}

.panel-header {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.panel-header h4 {
  flex: 1;
  margin: 0;
  font-size: 16px;
  color: #1a1a2e;
}

.panel-header .close-btn {
  margin-left: auto;
}

.panel-content {
  padding: 16px;
}

.detail-item {
  display: flex;
  margin-bottom: 12px;
}

.detail-item .detail-label {
  flex-shrink: 0;
  width: 80px;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
}

.detail-item .detail-value {
  flex: 1;
  font-size: 13px;
  color: #1a1a2e;
  word-break: break-all;
}

.detail-item .detail-value.uuid {
  font-family: monospace;
  font-size: 11px;
  color: #94a3b8;
}

.detail-section {
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.detail-section h5 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #1a1a2e;
}

.detail-value-array {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.array-tag {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
