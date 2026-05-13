<script lang="ts" setup>
import type { GraphNode } from '#/api/core/rag';

import { CircleClose } from '@element-plus/icons-vue';

import { entityColorService } from '#/services/entityColorService';

const props = defineProps<{
  filteredNodes: GraphNode[];
  isSearchFocused: boolean;
  searchQuery: string;
  selectedResultIndex: number;
  showSearchResults: boolean;
}>();

const emit = defineEmits<{
  nodeSelect: [node: GraphNode];
  searchAndLocate: [];
  'update:isSearchFocused': [value: boolean];
  'update:searchQuery': [value: string];
  'update:selectedResultIndex': [value: number];
  'update:showSearchResults': [value: boolean];
}>();

function onInput(e: Event) {
  const target = e.target as HTMLInputElement;
  emit('update:searchQuery', target.value);
  emit('update:showSearchResults', true);
  emit('update:selectedResultIndex', 0);
}

function onFocus() {
  emit('update:isSearchFocused', true);
  if (props.searchQuery) {
    emit('update:showSearchResults', true);
  }
}

function handleBlur() {
  setTimeout(() => {
    emit('update:isSearchFocused', false);
    emit('update:showSearchResults', false);
  }, 200);
}

function clearSearch() {
  emit('update:searchQuery', '');
  emit('update:showSearchResults', false);
  emit('update:selectedResultIndex', 0);
}

function navigateResults(direction: number) {
  if (props.filteredNodes.length === 0) return;
  let newIndex = props.selectedResultIndex + direction;
  if (newIndex < 0) {
    newIndex = props.filteredNodes.length - 1;
  } else if (newIndex >= props.filteredNodes.length) {
    newIndex = 0;
  }
  emit('update:selectedResultIndex', newIndex);
}

function selectAndLocateNode(node: GraphNode) {
  emit('nodeSelect', node);
  emit('update:searchQuery', node.name);
  emit('update:showSearchResults', false);
}
</script>

<template>
  <div class="node-search-container">
    <div class="search-input-wrapper">
      <input
        :value="searchQuery"
        type="text"
        placeholder="搜索节点..."
        class="search-input"
        @input="onInput"
        @focus="onFocus"
        @blur="handleBlur"
        @keydown.enter.prevent="$emit('searchAndLocate')"
        @keydown.down.prevent="navigateResults(1)"
        @keydown.up.prevent="navigateResults(-1)"
      />
      <span v-if="searchQuery" class="clear-icon" @click="clearSearch">
        <CircleClose />
      </span>
    </div>

    <div
      v-if="showSearchResults && filteredNodes.length > 0"
      class="search-results"
    >
      <div
        v-for="(node, index) in filteredNodes"
        :key="node.id"
        class="search-result-item"
        :class="[{ active: selectedResultIndex === index }]"
        @click="selectAndLocateNode(node)"
        @mouseenter="$emit('update:selectedResultIndex', index)"
      >
        <span
          class="result-dot"
          :style="{ background: entityColorService.getColor(node.category) }"
        ></span>
        <span class="result-name">{{ node.name }}</span>
        <span class="result-type">{{ node.category }}</span>
      </div>
    </div>

    <div
      v-else-if="showSearchResults && searchQuery && filteredNodes.length === 0"
      class="search-results no-results"
    >
      <span class="no-results-text">未找到匹配的节点</span>
    </div>
  </div>
</template>

<style scoped>
.node-search-container {
  position: relative;
  flex: 1;
  max-width: 260px;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 12px;
  background: rgb(255 255 255 / 95%);
  border: 1px solid rgb(226 232 240 / 80%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgb(0 0 0 / 10%);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.search-input-wrapper:focus-within {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 20px rgb(59 130 246 / 20%);
}

.search-input {
  flex: 1;
  height: 100%;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #1a1a2e;
  outline: none;
}

.search-input::placeholder {
  color: #94a3b8;
}

.clear-icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  font-size: 16px;
  color: #94a3b8;
  cursor: pointer;
}

.clear-icon:hover {
  color: #64748b;
}

.search-results {
  position: absolute;
  top: 52px;
  right: 0;
  left: 0;
  z-index: 101;
  max-height: 300px;
  overflow-y: auto;
  background: rgb(255 255 255 / 98%);
  border: 1px solid rgb(226 232 240 / 80%);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgb(0 0 0 / 15%);
  backdrop-filter: blur(10px);
}

.search-results.no-results {
  padding: 16px;
  text-align: center;
}

.search-result-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  transition: all 0.2s ease;
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover,
.search-result-item.active {
  background: var(--el-color-primary-light-9);
}

.search-result-item.active {
  border-left: 3px solid var(--el-color-primary);
}

.result-dot {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.result-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  white-space: nowrap;
}

.result-type {
  padding: 2px 8px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 4px;
}

.no-results-text {
  font-size: 14px;
  color: #94a3b8;
}
</style>
