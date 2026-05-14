<script lang="ts" setup>
import type { KnowledgeBase } from '#/api/core/rag';

import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { Plus, Search } from '@vben/icons';

import { ElButton, ElInput, ElMessage, ElPagination } from 'element-plus';

import {
  createKnowledgeBaseApi,
  getKnowledgeBaseListApi,
  updateKnowledgeBaseApi,
} from '#/api/core/rag';

import DescriptionEditor from './modules/description-editor.vue';
import DocCard from './modules/doc-card.vue';
import KbFormDialog from './modules/kb-form-dialog.vue';

defineOptions({ name: 'DocumentView' });

const router = useRouter();
const kbs = ref<KnowledgeBase[]>([]);
const searchQuery = ref('');
const loading = ref(false);
const descEditorRef = ref<InstanceType<typeof DescriptionEditor>>();
const formDialogRef = ref<InstanceType<typeof KbFormDialog>>();

const currentPage = ref(1);
const pageSize = ref(12);

const filteredKbs = computed(() => {
  if (!searchQuery.value.trim()) return kbs.value;
  const q = searchQuery.value.toLowerCase();
  return kbs.value.filter(
    (kb) =>
      kb.name.toLowerCase().includes(q) ||
      (kb.description || '').toLowerCase().includes(q),
  );
});

const paginatedKbs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredKbs.value.slice(start, start + pageSize.value);
});

const totalItems = computed(() => filteredKbs.value.length);

function handlePageChange(page: number) {
  currentPage.value = page;
}

function handleSearchInput(val: string) {
  searchQuery.value = val;
  currentPage.value = 1;
}

async function loadKbs() {
  loading.value = true;
  try {
    const res = await getKnowledgeBaseListApi({ page: 1, pageSize: 200 });
    kbs.value = res.items;
  } catch {
    ElMessage.error('加载知识库列表失败');
  } finally {
    loading.value = false;
  }
}

function handleCardClick(kb: KnowledgeBase) {
  router.push(`/rag/knowledge-base/${kb.id}`);
}

function handleCardAction(kb: KnowledgeBase) {
  router.push(`/rag/knowledge-base/${kb.id}`);
}

function openEdit(kb: KnowledgeBase) {
  descEditorRef.value?.open(kb);
}

function handleCreate() {
  formDialogRef.value?.open();
}

async function handleSave(
  data: { description?: string; name: string },
  editId?: string,
) {
  if (editId) {
    await updateKnowledgeBaseApi(editId, data);
    ElMessage.success('更新成功');
  } else {
    await createKnowledgeBaseApi(data);
    ElMessage.success('创建成功');
  }
  loadKbs();
}

onMounted(() => {
  loadKbs();
});
</script>

<template>
  <Page>
    <div class="document-view">
      <div class="page-header">
        <div class="header-left">
          <h2>知识库管理</h2>
          <span class="doc-count">{{ filteredKbs.length }} 个知识库</span>
        </div>
        <div class="header-right">
          <ElInput
            v-model="searchQuery"
            placeholder="搜索知识库..."
            clearable
            :prefix-icon="Search"
            style="width: 240px"
            @input="handleSearchInput"
            @update:model-value="handleSearchInput"
          />
          <ElButton type="primary" :icon="Plus" @click="handleCreate">
            新建知识库
          </ElButton>
        </div>
      </div>

      <div v-loading="loading" class="doc-grid">
        <div v-if="paginatedKbs.length === 0 && !loading" class="empty-state">
          <div
            style="
              padding: 60px 0;
              color: var(--el-text-color-secondary);
              text-align: center;
            "
          >
            <svg
              width="64"
              height="64"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1"
              style="margin-bottom: 16px"
            >
              <path
                d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
              />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <p>{{ searchQuery ? '未找到匹配的知识库' : '暂无知识库' }}</p>
            <ElButton
              v-if="!searchQuery"
              type="primary"
              style="margin-top: 12px"
              @click="handleCreate"
            >
              创建第一个知识库
            </ElButton>
          </div>
        </div>
        <DocCard
          v-for="kb in paginatedKbs"
          :key="kb.id"
          :kb="kb"
          :description="kb.description || ''"
          @click="handleCardClick(kb)"
          @edit="openEdit(kb)"
          @deleted="loadKbs"
          @view-graph="handleCardAction(kb)"
          @construct="handleCardAction(kb)"
          @upload-schema="handleCardAction(kb)"
        />
      </div>

      <div v-if="totalItems > pageSize" class="pagination-footer">
        <ElPagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalItems"
          layout="total, prev, pager, next"
          small
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <DescriptionEditor ref="descEditorRef" @saved="loadKbs" />
    <KbFormDialog ref="formDialogRef" @save="handleSave" />
  </Page>
</template>

<style scoped>
.document-view {
  padding: 8px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.header-left h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.doc-count {
  padding: 4px 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-lighter);
  border-radius: 12px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.doc-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.empty-state {
  grid-column: 1 / -1;
}

.pagination-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
}
</style>
