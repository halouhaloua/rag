<script lang="ts" setup>
import type { LayoutType } from '#/composables/useGraphLayout';

import { ref } from 'vue';

import { FolderOpen } from '@vben/icons';

import { Aim, Brush, Refresh } from '@element-plus/icons-vue';
import {
  ElDivider,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElIcon,
  ElTooltip,
} from 'element-plus';

import {
  entityColorService,
  presetColorSchemes,
} from '#/services/entityColorService';

import GraphLayoutControl from './GraphLayoutControl.vue';

defineProps<{
  currentLayout: LayoutType;
  fileLabel?: string;
  kbName?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  colorSchemeChange: [schemeKey: string];
  layoutChange: [layout: LayoutType];
  openSelector: [];
  refresh: [];
  reset: [];
}>();

const currentSchemeKey = ref<string>('vibrant');

function getSchemePreviewColors(schemeKey: string): string[] {
  const scheme = presetColorSchemes[schemeKey];
  if (!scheme) return [];
  const colors: string[] = [];
  for (let i = 0; i < 5; i++) {
    const { baseHue, hueRange, saturation, lightness } = scheme;
    const hueStep = hueRange / 5;
    const hue = (baseHue + i * hueStep) % 360;
    const sat = (saturation[0] + saturation[1]) / 2;
    const light = (lightness[0] + lightness[1]) / 2;
    const s = sat / 100;
    const l = light / 100;
    const a = s * Math.min(l, 1 - l);
    const f = (n: number) => {
      const k = (n + hue / 30) % 12;
      const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
      return Math.round(255 * color)
        .toString(16)
        .padStart(2, '0');
    };
    colors.push(`#${f(0)}${f(8)}${f(4)}`);
  }
  return colors;
}

function handleSchemeChange(schemeKey: string) {
  currentSchemeKey.value = schemeKey;
  entityColorService.setSchemeByName(schemeKey);
  emit('colorSchemeChange', schemeKey);
}
</script>

<template>
  <div class="floating-toolbar">
    <div class="toolbar-group">
      <ElTooltip content="选择知识库和文件" placement="bottom">
        <div class="dataset-selector-btn" @click="$emit('openSelector')">
          <ElIcon :size="18"><FolderOpen /></ElIcon>
        </div>
      </ElTooltip>

      <span v-if="kbName" class="dataset-label">
        {{ kbName }}{{ fileLabel ? ` / ${fileLabel}` : '' }}
      </span>

      <ElDivider direction="vertical" />

      <ElDropdown
        trigger="click"
        placement="bottom-start"
        @command="handleSchemeChange"
      >
        <div class="color-btn" @click.stop>
          <ElIcon :size="18"><Brush /></ElIcon>
        </div>
        <template #dropdown>
          <ElDropdownMenu class="color-scheme-menu">
            <ElDropdownItem
              v-for="(scheme, key) in presetColorSchemes"
              :key="key"
              :command="key"
              :class="{ 'is-active': currentSchemeKey === key }"
            >
              <div class="scheme-option">
                <span class="scheme-name">{{ scheme.name }}</span>
                <div class="scheme-preview">
                  <span
                    v-for="(color, i) in getSchemePreviewColors(key as string)"
                    :key="i"
                    class="preview-dot"
                    :style="{ background: color }"
                  ></span>
                </div>
              </div>
            </ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>

      <ElDivider direction="vertical" />

      <GraphLayoutControl
        :current-layout="currentLayout"
        @layout-change="(l: LayoutType) => emit('layoutChange', l)"
      />

      <ElTooltip content="刷新图谱数据" placement="bottom">
        <div class="toolbar-btn" @click="$emit('refresh')">
          <ElIcon :size="18"><Refresh /></ElIcon>
        </div>
      </ElTooltip>

      <ElTooltip content="重置视图" placement="bottom">
        <div class="toolbar-btn" @click="$emit('reset')">
          <ElIcon :size="18"><Aim /></ElIcon>
        </div>
      </ElTooltip>
    </div>
  </div>
</template>

<style scoped>
.floating-toolbar {
  position: absolute;
  top: 12px;
  right: 16px;
  z-index: 40;
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}

.toolbar-group {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 8px 16px;
  pointer-events: auto;
  background: rgb(255 255 255 / 95%);
  border: 1px solid rgb(226 232 240 / 80%);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgb(0 0 0 / 8%);
  backdrop-filter: blur(10px);
}

.toolbar-group :deep(.el-divider) {
  height: 20px;
  margin: 0 4px;
}

.dataset-selector-btn {
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

.dataset-selector-btn:hover {
  background: #ede9fe;
  transform: scale(1.05);
}

.dataset-selector-btn:active {
  transform: scale(0.95);
}

.color-btn {
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

.color-btn:hover {
  background: #ede9fe;
  transform: scale(1.05);
}

.color-btn:active {
  transform: scale(0.95);
}

.dataset-label {
  max-width: 200px;
  padding: 4px 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  white-space: nowrap;
  background: #f1f5f9;
  border-radius: 20px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  color: var(--el-color-primary);
  cursor: pointer;
  background: #f5f3ff;
  border: none;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  background: #ede9fe;
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgb(0 0 0 / 10%);
}

.toolbar-btn:active {
  transform: scale(0.95);
}
</style>

<style>
.color-scheme-menu .scheme-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 160px;
}

.color-scheme-menu .scheme-name {
  font-size: 13px;
}

.color-scheme-menu .scheme-preview {
  display: flex;
  gap: 3px;
}

.color-scheme-menu .preview-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
</style>
