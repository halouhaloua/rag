<script lang="ts" setup>
import type { LayoutType } from '#/composables/useGraphLayout';

import { Check, Grid } from '@element-plus/icons-vue';
import {
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElIcon,
  ElTooltip,
} from 'element-plus';

import { LAYOUT_OPTIONS as layouts } from '#/composables/useGraphLayout';

defineProps<{
  currentLayout: LayoutType;
}>();

const emit = defineEmits<{
  layoutChange: [layout: LayoutType];
}>();

const LAYOUT_OPTIONS = layouts;

function handleSelect(key: string) {
  emit('layoutChange', key as LayoutType);
}
</script>

<template>
  <ElTooltip content="切换布局" placement="bottom">
    <ElDropdown
      trigger="click"
      placement="bottom-start"
      @command="handleSelect"
    >
      <div class="layout-btn" @click.stop>
        <ElIcon :size="18"><Grid /></ElIcon>
      </div>
      <template #dropdown>
        <ElDropdownMenu class="layout-dropdown-menu">
          <ElDropdownItem
            v-for="opt in LAYOUT_OPTIONS"
            :key="opt.key"
            :command="opt.key"
            :class="{ 'is-active': currentLayout === opt.key }"
          >
            <span class="layout-item">
              <span class="layout-dot" :class="opt.key"></span>
              <span>{{ opt.label }}</span>
              <ElIcon v-if="currentLayout === opt.key" class="check-icon">
                <Check />
              </ElIcon>
            </span>
          </ElDropdownItem>
        </ElDropdownMenu>
      </template>
    </ElDropdown>
  </ElTooltip>
</template>

<style scoped>
.layout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  color: var(--el-color-primary);
  cursor: pointer;
  background: #f5f3ff;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.layout-btn:hover {
  background: #ede9fe;
  transform: scale(1.05);
}

.layout-btn:active {
  transform: scale(0.95);
}
</style>

<style>
.layout-dropdown-menu .layout-item {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 150px;
  font-size: 13px;
}

.layout-dropdown-menu .check-icon {
  margin-left: auto;
  font-size: 14px;
  color: var(--el-color-primary);
}

.layout-dropdown-menu .layout-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.layout-dropdown-menu .layout-dot.force {
  background: #6366f1;
}

.layout-dropdown-menu .layout-dot.circular {
  background: #10b981;
}

.layout-dropdown-menu .layout-dot.static-force {
  background: #f59e0b;
}

.layout-dropdown-menu .layout-dot.noverlaps {
  background: #8b5cf6;
}

.layout-dropdown-menu .layout-dot.force-atlas-2 {
  background: #06b6d4;
}

.layout-dropdown-menu .is-active {
  font-weight: 600;
  color: var(--el-color-primary);
}
</style>
