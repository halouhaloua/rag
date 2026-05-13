<script lang="ts" setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { Page } from '@vben/common-ui';
import { Edit, Plus, Trash2 } from '@vben/icons';
import { ElButton, ElMessage, ElMessageBox, ElTag } from 'element-plus';
import { useZqTable } from '#/components/zq-table';
import {
  getKnowledgeBaseListApi,
  createKnowledgeBaseApi,
  updateKnowledgeBaseApi,
  deleteKnowledgeBaseApi,
  type KnowledgeBase,
} from '#/api/core/rag';
import KbFormDialog from './modules/kb-form-dialog.vue';

defineOptions({ name: 'KnowledgeBaseManager' });

const router = useRouter();
const formDialogRef = ref<InstanceType<typeof KbFormDialog>>();

const fetchList = async (params: any) => {
  const res = await getKnowledgeBaseListApi({
    page: params.page.currentPage,
    pageSize: params.page.pageSize,
  });
  return { items: res.items, total: res.total };
};

const [Grid, gridApi] = useZqTable({
  gridOptions: {
    columns: [
      { key: 'name', title: '知识库名称', minWidth: 160 },
      { key: 'description', title: '描述', minWidth: 200, showOverflow: 'tooltip' },
      {
        key: 'kb_type',
        title: '类型',
        width: 90,
        slots: { default: 'cell-type' },
      },
      { key: 'file_count', title: '文件数', width: 80 },
      { key: 'sys_create_datetime', title: '创建时间', width: 170 },
      {
        key: 'actions',
        title: '操作',
        width: 200,
        slots: { default: 'cell-actions' },
        fixed: true,
      },
    ],
    border: true,
    stripe: true,
    showSelection: false,
    showIndex: true,
    proxyConfig: { autoLoad: true, ajax: { query: fetchList } },
    pagerConfig: { enabled: true, pageSize: 20 },
    toolbarConfig: { search: false, refresh: true, zoom: true, custom: true },
  },
  formOptions: {
    schema: [],
    showCollapseButton: false,
    submitOnChange: false,
  },
});

function onCreate() {
  formDialogRef.value?.open();
}

function onEdit(row: KnowledgeBase) {
  formDialogRef.value?.open(row);
}

async function onDelete(row: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(
      `确定删除知识库「${row.name}」？该操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    );
    await deleteKnowledgeBaseApi(row.id);
    ElMessage.success('删除成功');
    gridApi.reload();
  } catch {
    // cancelled
  }
}

function onView(row: KnowledgeBase) {
  router.push(`/rag/knowledge-base/${row.id}`);
}

async function handleSave(data: { name: string; description?: string }, editId?: string) {
  if (editId) {
    await updateKnowledgeBaseApi(editId, data);
    ElMessage.success('更新成功');
  } else {
    await createKnowledgeBaseApi(data);
    ElMessage.success('创建成功');
  }
  gridApi.reload();
}
</script>

<template>
  <Page>
    <Grid>
      <template #toolbar-actions>
        <ElButton type="primary" :icon="Plus" @click="onCreate">
          创建知识库
        </ElButton>
      </template>

      <template #cell-type="{ row }">
        <ElTag :type="row.kb_type === 'demo' ? 'success' : 'primary'" size="small">
          {{ row.kb_type === 'demo' ? '演示' : '用户' }}
        </ElTag>
      </template>

      <template #cell-actions="{ row }">
        <ElButton link type="primary" @click="onView(row)">
          管理
        </ElButton>
        <ElButton link type="primary" :icon="Edit" @click="onEdit(row)">
          编辑
        </ElButton>
        <ElButton link type="danger" :icon="Trash2" @click="onDelete(row)">
          删除
        </ElButton>
      </template>
    </Grid>

    <KbFormDialog ref="formDialogRef" @save="handleSave" />
  </Page>
</template>
