<script lang="ts" setup>
import type { Role } from '#/api/core/role';
import type { KnowledgeBase } from '#/api/core/rag';

import { ref, watch, computed } from 'vue';
import {
  ElButton,
  ElCard,
  ElCheckbox,
  ElEmpty,
  ElInput,
  ElMessage,
  ElScrollbar,
  ElSkeleton,
  ElSkeletonItem,
  ElTag,
} from 'element-plus';
import {
  getKnowledgeBaseListApi,
  getRoleKbPermissionsApi,
  updateRoleKbPermissionsApi,
} from '#/api/core/rag';

interface Props {
  role?: Role;
}
const props = defineProps<Props>();
const emit = defineEmits<{ success: [] }>();

const loading = ref(false);
const saving = ref(false);
const allKbs = ref<KnowledgeBase[]>([]);
const selectedMap = ref<Record<string, boolean>>({});
const searchQuery = ref('');

const filteredKbs = computed(() => {
  if (!searchQuery.value) return allKbs.value;
  const q = searchQuery.value.toLowerCase();
  return allKbs.value.filter((kb) => kb.name.toLowerCase().includes(q));
});

const allSelected = computed(
  () =>
    allKbs.value.length > 0 &&
    allKbs.value.every((kb) => selectedMap.value[kb.id]),
);

const selectedCount = computed(
  () => Object.values(selectedMap.value).filter(Boolean).length,
);

function toggleAll(checked: boolean) {
  const newMap: Record<string, boolean> = {};
  if (checked) {
    allKbs.value.forEach((kb) => {
      newMap[kb.id] = true;
    });
  }
  selectedMap.value = { ...newMap };
}

async function loadData() {
  if (!props.role?.id) return;
  loading.value = true;
  try {
    const [allRes, roleKbsRes] = await Promise.all([
      getKnowledgeBaseListApi({ page: 1, pageSize: 500 }),
      getRoleKbPermissionsApi(props.role.id),
    ]);
    allKbs.value = allRes.items ?? [];
    const map: Record<string, boolean> = {};
    for (const kb of roleKbsRes.items ?? []) {
      map[kb.id] = true;
    }
    selectedMap.value = map;
  } catch (error) {
    console.error('加载知识库数据失败', error);
    ElMessage.error('加载知识库数据失败');
  } finally {
    loading.value = false;
  }
}

watch(
  () => props.role?.id,
  (id) => {
    searchQuery.value = '';
    if (id) {
      loadData();
    } else {
      allKbs.value = [];
      selectedMap.value = {};
    }
  },
);

function toggleKb(kbId: string, checked: boolean) {
  selectedMap.value = { ...selectedMap.value, [kbId]: checked };
}

function selectAll() {
  toggleAll(true);
}

function unselectAll() {
  toggleAll(false);
}

async function saveSelection() {
  if (!props.role?.id) return;
  saving.value = true;
  try {
    const kbIds = Object.entries(selectedMap.value)
      .filter(([, v]) => v)
      .map(([k]) => k);
    await updateRoleKbPermissionsApi(props.role.id, kbIds);
    ElMessage.success('知识库权限更新成功');
    emit('success');
  } catch (error) {
    console.error('保存知识库权限失败', error);
    ElMessage.error('保存知识库权限失败');
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <ElCard
    class="h-full"
    :class="[role ? 'flex flex-col' : 'empty-state-card']"
    shadow="never"
    style="border: none"
    :body-style="!role ? { height: '100%', padding: 0 } : { padding: '6px' }"
  >
    <!-- 未选择角色 -->
    <div v-if="!role" class="flex h-full w-full items-center justify-center">
      <ElEmpty description="请先选择一个角色" />
    </div>

    <!-- 头部 -->
    <template v-if="role" #header>
      <div class="flex w-full items-center justify-between">
        <div class="flex items-center gap-4">
          <span class="text-base font-medium">知识库权限</span>
          <span class="text-sm text-gray-500">
            {{ role.name }} ({{ role.code }})
          </span>
        </div>
        <ElButton
          :loading="saving"
          type="primary"
          size="small"
          @click="saveSelection"
        >
          保存
        </ElButton>
      </div>
    </template>

    <!-- 主内容区 -->
    <div v-if="role" class="flex flex-1 flex-col overflow-hidden">
      <!-- 加载骨架屏 -->
      <div v-if="loading" class="flex-1 p-3">
        <ElCard
          class="h-full border border-[var(--el-border-color)]"
          shadow="never"
        >
          <ElSkeleton :loading="true" animated :throttle="0">
            <template #template>
              <div class="space-y-2 p-2">
                <div
                  v-for="i in 10"
                  :key="i"
                  class="flex h-[42px] items-center gap-3"
                >
                  <ElSkeletonItem
                    variant="text"
                    style="width: 16px; height: 16px; border-radius: 4px"
                  />
                  <ElSkeletonItem
                    variant="text"
                    :style="{
                      width: `${50 + Math.random() * 40}%`,
                      height: '16px',
                    }"
                  />
                </div>
              </div>
            </template>
          </ElSkeleton>
        </ElCard>
      </div>

      <!-- 空状态 -->
      <div
        v-else-if="allKbs.length === 0"
        class="flex flex-1 items-center justify-center"
      >
        <ElEmpty description="暂无知识库数据" />
      </div>

      <!-- 正常内容 -->
      <div v-else class="flex min-h-0 flex-1 flex-col gap-3 p-3">
        <!-- 工具栏：搜索 + 全选 -->
        <div
          class="flex items-center justify-between rounded-[var(--el-border-radius-base)] border border-[var(--el-border-color)] bg-white px-4 py-3"
        >
          <div class="flex items-center gap-4">
            <ElInput
              v-model="searchQuery"
              placeholder="搜索知识库..."
              clearable
              style="width: 280px"
              size="small"
            />
            <span class="text-xs text-gray-400">
              已选 {{ selectedCount }}/{{ allKbs.length }}
            </span>
          </div>
          <div class="flex gap-1">
            <ElButton link type="primary" size="small" @click="selectAll">
              全选
            </ElButton>
            <ElButton link type="primary" size="small" @click="unselectAll">
              取消全选
            </ElButton>
          </div>
        </div>

        <!-- 知识库列表卡片 -->
        <ElCard
          class="min-h-0 flex-1 border border-[var(--el-border-color)]"
          shadow="never"
          :body-style="{
            padding: '0',
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }"
        >
          <ElScrollbar class="flex-1">
            <div
              v-if="filteredKbs.length === 0"
              class="flex items-center justify-center py-12"
            >
              <span class="text-xs text-gray-400">
                {{ searchQuery ? '无匹配的知识库' : '暂无知识库数据' }}
              </span>
            </div>
            <div v-else class="p-2">
              <div
                v-for="kb in filteredKbs"
                :key="kb.id"
                class="flex h-[36px] cursor-pointer items-center rounded-[6px] px-2 transition-colors hover:bg-[var(--el-fill-color-light)]"
                @click="toggleKb(kb.id, !selectedMap[kb.id])"
              >
                <input
                  type="checkbox"
                  :checked="!!selectedMap[kb.id]"
                  class="mr-2 size-3.5 flex-shrink-0 cursor-pointer rounded border-gray-300 transition-colors"
                  @change="
                    toggleKb(kb.id, ($event.target as HTMLInputElement).checked)
                  "
                  @click.stop
                />
                <span class="flex-1 truncate text-xs" :title="kb.name">
                  {{ kb.name }}
                </span>
                <ElTag
                  v-if="kb.kb_type === 'demo'"
                  size="small"
                  type="info"
                  class="flex-shrink-0"
                  style="height: 20px; line-height: 20px"
                >
                  演示
                </ElTag>
                <span class="ml-2 flex-shrink-0 text-xs text-gray-400">
                  {{ kb.file_count }} 个文件
                </span>
                <span
                  v-if="kb.description"
                  class="ml-2 max-w-48 flex-shrink-0 truncate text-xs text-gray-400"
                  :title="kb.description"
                >
                  {{ kb.description }}
                </span>
              </div>
            </div>
          </ElScrollbar>
        </ElCard>
      </div>
    </div>
  </ElCard>
</template>

<style scoped>
.empty-state-card :deep(.el-card__body) {
  height: 100%;
  padding: 0;
}
</style>
