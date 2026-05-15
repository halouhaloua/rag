<script lang="ts" setup>
import type { Role } from '#/api/core/role';

import { ref } from 'vue';

import { Page } from '@vben/common-ui';
import { $t } from '@vben/locales';
import { ElTabPane, ElTabs } from 'element-plus';

import { getRoleDetailApi } from '#/api/core/role';

import PermissionAssignPanel from './modules/permission-assign-panel.vue';
import KbPermissionPanel from './modules/kb-permission-panel.vue';
import RoleList from './modules/role-list.vue';

defineOptions({ name: 'SystemRole' });

const activeTab = ref('menu');
const currentRole = ref<Role>();
const permissionPanelRef = ref();

/**
 * 角色选择事件
 */
async function onRoleSelect(roleId: string | undefined) {
  if (roleId) {
    try {
      const role = await getRoleDetailApi(roleId);
      currentRole.value = role;
    } catch (error) {
      console.error($t('role.permissions.getRoleDetailFailed'), error);
      currentRole.value = undefined;
    }
  } else {
    currentRole.value = undefined;
  }
}

/**
 * 权限分配成功
 */
function onPermissionSuccess() {
  // 权限分配成功，可以在这里做其他操作
}
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full">
      <!-- 左侧：角色列表 -->
      <div class="w-1/6">
        <RoleList @select="onRoleSelect" />
      </div>

      <!-- 右侧：Tabs 切换菜单权限/知识库权限 -->
      <div class="flex w-5/6 min-w-0 flex-col">
        <ElTabs v-model="activeTab" class="role-tabs">
          <ElTabPane label="菜单权限" name="menu">
            <PermissionAssignPanel
              ref="permissionPanelRef"
              :role="currentRole"
              @success="onPermissionSuccess"
            />
          </ElTabPane>
          <ElTabPane label="知识库权限" name="kb">
            <KbPermissionPanel
              :role="currentRole"
              @success="onPermissionSuccess"
            />
          </ElTabPane>
        </ElTabs>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.role-tabs {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

/* 简约风格 Tab 栏 —— 独立 header 栏，不与下方区域连接 */
.role-tabs :deep(.el-tabs__header) {
  margin: 0 0 8px 0;          /* 下方留白，与内容区域分离 */
  padding: 0 0 0 20px;         /* 左侧增加内边距，让文字整体向右移动 */
  background-color: #ffffff;    /* 纯白背景，形成独立栏 */
  border-radius: 8px;           /* 圆角，更像卡片头部 */
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03), 0 1px 4px rgba(0, 0, 0, 0.02); /* 极浅阴影，提升层次感 */
  border: 1px solid #eff0f2;    /* 浅灰边框，增强独立性 */
}

.role-tabs :deep(.el-tabs__nav-wrap) {
  margin-bottom: -1px;          /* 与底部边框对齐 */
}

/* 移除原生下划线装饰，保留激活指示条 */
.role-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

/* Tab 项样式 */
.role-tabs :deep(.el-tabs__item) {
  height: 44px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 400;
  color: #5c6b7e;
  transition: color 0.2s ease;
}

/* 悬停效果 */
.role-tabs :deep(.el-tabs__item:hover) {
  color: #2c3e50;
}

/* 激活的 Tab 项 */
.role-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 500;
  color: var(--el-color-primary, #409eff);
}

/* 激活指示条 —— 纯色，无渐变 */
.role-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  background-color: var(--el-color-primary, #409eff);
  border-radius: 0;
}

/* 内容区域独立，不再与 header 视觉连接 */
.role-tabs :deep(.el-tabs__content) {
  flex: 1;
  padding: 0;
  min-height: 0;
  overflow: hidden;
  background-color: transparent;
}

.role-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow: hidden;
}
</style>