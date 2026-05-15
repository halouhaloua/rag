<script lang="ts" setup>
import type { GraphLink, GraphNode, KnowledgeBaseFile, PaginatedGraphItems } from '#/api/core/rag';
import { onMounted, ref, watch } from 'vue';
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElMessage,
  ElMessageBox,
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTabPane,
  ElTabs,
  ElTag,
} from 'element-plus';
import { Plus, Trash2 } from '@vben/icons';

import {
  addGraphEdgesApi,
  addGraphNodesApi,
  deleteGraphEdgeApi,
  deleteGraphNodeApi,
  getFileListApi,
  getGraphEdgesApi,
  getGraphNodesApi,
  updateGraphEdgeApi,
  updateNodeCategoryApi,
} from '#/api/core/rag';

const props = defineProps<{ kbId: string }>();

const files = ref<KnowledgeBaseFile[]>([]);
const selectedFileId = ref('');
const loadingNodes = ref(false);
const loadingEdges = ref(false);
const activeSubTab = ref('nodes');

// ─── Paginated nodes ───
const nodeRes = ref<PaginatedGraphItems<GraphNode>>({ items: [], total: 0 });
const nodePage = ref(1);
const nodePageSize = ref(20);

// ─── Paginated edges ───
const edgeRes = ref<PaginatedGraphItems<GraphLink>>({ items: [], total: 0 });
const edgePage = ref(1);
const edgePageSize = ref(20);

// ─── Load files ───

async function loadFiles() {
  const res = await getFileListApi(props.kbId);
  files.value = res.items.filter((f) => f.has_graph);
  if (files.value.length > 0 && !selectedFileId.value) {
    selectedFileId.value = files.value[0]!.id;
  }
}

async function loadNodes(fileId: string) {
  if (!fileId) return;
  loadingNodes.value = true;
  try {
    nodeRes.value = await getGraphNodesApi(props.kbId, fileId, nodePage.value, nodePageSize.value);
  } catch {
    ElMessage.error('加载节点列表失败');
    nodeRes.value = { items: [], total: 0 };
  } finally {
    loadingNodes.value = false;
  }
}

async function loadEdges(fileId: string) {
  if (!fileId) return;
  loadingEdges.value = true;
  try {
    edgeRes.value = await getGraphEdgesApi(props.kbId, fileId, edgePage.value, edgePageSize.value);
  } catch {
    ElMessage.error('加载边列表失败');
    edgeRes.value = { items: [], total: 0 };
  } finally {
    loadingEdges.value = false;
  }
}

// ─── Derived data ───

// ─── Node operations ───

const addNodeDialogVisible = ref(false);
const addNodeForm = ref({ name: '', category: 'entity' });

async function handleAddNode() {
  if (!addNodeForm.value.name.trim()) {
    ElMessage.warning('请输入节点名称');
    return;
  }
  try {
    await addGraphNodesApi(props.kbId, selectedFileId.value, [
      { name: addNodeForm.value.name.trim(), category: addNodeForm.value.category },
    ]);
    ElMessage.success('节点添加成功');
    addNodeDialogVisible.value = false;
    addNodeForm.value = { name: '', category: 'entity' };
    nodePage.value = 1;
    await loadNodes(selectedFileId.value);
  } catch (error: any) {
    ElMessage.error(error.message || '添加节点失败');
  }
}

const editCategoryDialogVisible = ref(false);
const editCategoryForm = ref({ nodeName: '', currentCategory: '', newCategory: '' });

function openEditCategory(nodeName: string, currentCategory: string) {
  editCategoryForm.value = { nodeName, currentCategory, newCategory: currentCategory };
  editCategoryDialogVisible.value = true;
}

async function handleEditCategory() {
  if (!editCategoryForm.value.newCategory.trim()) {
    ElMessage.warning('请输入类别');
    return;
  }
  try {
    await updateNodeCategoryApi(
      props.kbId,
      selectedFileId.value,
      editCategoryForm.value.nodeName,
      editCategoryForm.value.newCategory.trim(),
    );
    ElMessage.success('类别更新成功');
    editCategoryDialogVisible.value = false;
    await loadNodes(selectedFileId.value);
  } catch (error: any) {
    ElMessage.error(error.message || '更新类别失败');
  }
}

async function handleDeleteNode(nodeName: string) {
  try {
    await ElMessageBox.confirm(
      `确定删除节点「${nodeName}」？所有关联的边将一并删除。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    );
    await deleteGraphNodeApi(props.kbId, selectedFileId.value, nodeName);
    ElMessage.success('节点删除成功');
    nodePage.value = 1;
    await loadNodes(selectedFileId.value);
    edgePage.value = 1;
    await loadEdges(selectedFileId.value);
  } catch {
    // cancelled or error
  }
}

// ─── Edge operations ───

const addEdgeDialogVisible = ref(false);
const addEdgeForm = ref({ source: '', relation: '', target: '', source_category: 'entity', target_category: 'entity' });

async function handleAddEdge() {
  if (!addEdgeForm.value.source.trim() || !addEdgeForm.value.relation.trim() || !addEdgeForm.value.target.trim()) {
    ElMessage.warning('请完整填写源节点、关系、目标节点');
    return;
  }
  try {
    await addGraphEdgesApi(props.kbId, selectedFileId.value, [
      {
        source: addEdgeForm.value.source.trim(),
        relation: addEdgeForm.value.relation.trim(),
        target: addEdgeForm.value.target.trim(),
        source_category: addEdgeForm.value.source_category,
        target_category: addEdgeForm.value.target_category,
      },
    ]);
    ElMessage.success('边添加成功');
    addEdgeDialogVisible.value = false;
    addEdgeForm.value = { source: '', relation: '', target: '', source_category: 'entity', target_category: 'entity' };
    edgePage.value = 1;
    await loadEdges(selectedFileId.value);
  } catch (error: any) {
    ElMessage.error(error.message || '添加边失败');
  }
}

async function handleDeleteEdge(source: string, relation: string, target: string) {
  try {
    await ElMessageBox.confirm(
      `确定删除边「${source} → ${relation} → ${target}」？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    );
    await deleteGraphEdgeApi(props.kbId, selectedFileId.value, source, relation, target);
    ElMessage.success('边删除成功');
    edgePage.value = 1;
    await loadEdges(selectedFileId.value);
  } catch {
    // cancelled or error
  }
}

// ─── Edge edit operations ───

const editEdgeDialogVisible = ref(false);
const editEdgeForm = ref<{
  oldSource: string; oldRelation: string; oldTarget: string;
  source: string; relation: string; target: string;
  source_category: string; target_category: string;
}>({
  oldSource: '', oldRelation: '', oldTarget: '',
  source: '', relation: '', target: '',
  source_category: 'entity', target_category: 'entity',
});

function openEditEdge(row: { source: string; name: string; target: string }) {
  editEdgeForm.value = {
    oldSource: row.source,
    oldRelation: row.name,
    oldTarget: row.target,
    source: row.source,
    relation: row.name,
    target: row.target,
    source_category: 'entity',
    target_category: 'entity',
  };
  editEdgeDialogVisible.value = true;
}

async function handleEditEdge() {
  if (!editEdgeForm.value.source.trim() || !editEdgeForm.value.relation.trim() || !editEdgeForm.value.target.trim()) {
    ElMessage.warning('请完整填写源节点、关系、目标节点');
    return;
  }
  try {
    await updateGraphEdgeApi(props.kbId, selectedFileId.value, {
      source: editEdgeForm.value.oldSource,
      relation: editEdgeForm.value.oldRelation,
      target: editEdgeForm.value.oldTarget,
      new_source: editEdgeForm.value.source !== editEdgeForm.value.oldSource ? editEdgeForm.value.source.trim() : undefined,
      new_relation: editEdgeForm.value.relation !== editEdgeForm.value.oldRelation ? editEdgeForm.value.relation.trim() : undefined,
      new_target: editEdgeForm.value.target !== editEdgeForm.value.oldTarget ? editEdgeForm.value.target.trim() : undefined,
      new_source_category: editEdgeForm.value.source_category,
      new_target_category: editEdgeForm.value.target_category,
    });
    ElMessage.success('边编辑成功');
    editEdgeDialogVisible.value = false;
    edgePage.value = 1;
    await loadEdges(selectedFileId.value);
  } catch (error: any) {
    ElMessage.error(error.message || '编辑边失败');
  }
}

// ─── Watchers ───

watch(selectedFileId, (fileId) => {
  if (!fileId) return;
  nodePage.value = 1;
  edgePage.value = 1;
  loadNodes(fileId);
  loadEdges(fileId);
});

watch([nodePage, nodePageSize], () => {
  if (selectedFileId.value) loadNodes(selectedFileId.value);
});

watch([edgePage, edgePageSize], () => {
  if (selectedFileId.value) loadEdges(selectedFileId.value);
});

onMounted(() => {
  loadFiles();
});
</script>

<template>
  <div class="triple-tab">
    <div class="file-selector">
      <span class="label">选择文件：</span>
      <ElSelect
        v-model="selectedFileId"
        placeholder="选择已构建图谱的文件"
        style="width: 280px"
        size="small"
      >
        <ElOption
          v-for="f in files"
          :key="f.id"
          :label="f.filename"
          :value="f.id"
        />
      </ElSelect>
      <span v-if="files.length === 0" class="no-data-hint">
        暂无已构建图谱的文件
      </span>
    </div>

    <div class="triple-content">
      <div class="graph-summary">
        <span>节点: {{ nodeRes.total }}</span>
        <span class="sep">|</span>
        <span>边: {{ edgeRes.total }}</span>
      </div>

      <ElTabs v-model="activeSubTab" class="sub-tabs">
        <!-- ─── 节点管理 ─── -->
        <ElTabPane label="节点管理" name="nodes">
          <div class="tab-body">
            <div class="toolbar">
              <ElButton type="primary" size="small" :icon="Plus" @click="addNodeDialogVisible = true">
                添加节点
              </ElButton>
            </div>
            <ElTable :data="nodeRes.items" border size="small" max-height="400" v-loading="loadingNodes">
              <ElTableColumn prop="name" label="名称" min-width="160" show-overflow-tooltip />
              <ElTableColumn prop="category" label="类别" width="140">
                <template #default="{ row }">
                  <ElTag :type="row.category === 'attribute' ? 'warning' : 'primary'" size="small">
                    {{ row.category }}
                  </ElTag>
                </template>
              </ElTableColumn>
              <ElTableColumn label="操作" width="180" fixed="right">
                <template #default="{ row }">
                  <ElButton
                    size="small"
                    type="primary"
                    link
                    @click="openEditCategory(row.name, row.category)"
                  >
                    编辑分类
                  </ElButton>
                  <ElButton
                    size="small"
                    type="danger"
                    link
                    :icon="Trash2"
                    @click="handleDeleteNode(row.name)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
            <div class="pagination-wrap">
              <ElPagination
                v-model:current-page="nodePage"
                v-model:page-size="nodePageSize"
                :total="nodeRes.total"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next"
                small
              />
            </div>
          </div>
        </ElTabPane>

        <!-- ─── 边管理 ─── -->
        <ElTabPane label="边管理" name="edges">
          <div class="tab-body">
            <div class="toolbar">
              <ElButton type="primary" size="small" :icon="Plus" @click="addEdgeDialogVisible = true">
                添加边
              </ElButton>
            </div>
            <ElTable :data="edgeRes.items" border size="small" max-height="400" v-loading="loadingEdges">
              <ElTableColumn prop="source" label="源节点" min-width="160" show-overflow-tooltip />
              <ElTableColumn prop="name" label="关系" width="140" />
              <ElTableColumn prop="target" label="目标节点" min-width="160" show-overflow-tooltip />
              <ElTableColumn label="操作" width="160" fixed="right">
                <template #default="{ row }">
                  <ElButton
                    size="small"
                    type="primary"
                    link
                    @click="openEditEdge(row)"
                  >
                    编辑
                  </ElButton>
                  <ElButton
                    size="small"
                    type="danger"
                    link
                    :icon="Trash2"
                    @click="handleDeleteEdge(row.source, row.name, row.target)"
                  >
                    删除
                  </ElButton>
                </template>
              </ElTableColumn>
            </ElTable>
            <div class="pagination-wrap">
              <ElPagination
                v-model:current-page="edgePage"
                v-model:page-size="edgePageSize"
                :total="edgeRes.total"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next"
                small
              />
            </div>
          </div>
        </ElTabPane>
      </ElTabs>
    </div>

    <!-- ─── Add Node Dialog ─── -->
    <ElDialog v-model="addNodeDialogVisible" title="添加节点" width="420px">
      <ElForm label-width="80px">
        <ElFormItem label="名称" required>
          <ElInput v-model="addNodeForm.name" placeholder="节点名称" />
        </ElFormItem>
        <ElFormItem label="类别">
          <ElInput v-model="addNodeForm.category" placeholder="entity" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="addNodeDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="handleAddNode">确定</ElButton>
      </template>
    </ElDialog>

    <!-- ─── Add Edge Dialog ─── -->
    <ElDialog v-model="addEdgeDialogVisible" title="添加边" width="480px">
      <ElForm label-width="120px">
        <ElFormItem label="源节点" required>
          <ElInput v-model="addEdgeForm.source" placeholder="源节点名称" />
        </ElFormItem>
        <ElFormItem label="源节点类别">
          <ElInput v-model="addEdgeForm.source_category" placeholder="entity" />
        </ElFormItem>
        <ElFormItem label="关系" required>
          <ElInput v-model="addEdgeForm.relation" placeholder="关系类型" />
        </ElFormItem>
        <ElFormItem label="目标节点" required>
          <ElInput v-model="addEdgeForm.target" placeholder="目标节点名称" />
        </ElFormItem>
        <ElFormItem label="目标节点类别">
          <ElInput v-model="addEdgeForm.target_category" placeholder="entity" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="addEdgeDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="handleAddEdge">确定</ElButton>
      </template>
    </ElDialog>

    <!-- ─── Edit Category Dialog ─── -->
    <ElDialog v-model="editCategoryDialogVisible" title="编辑节点分类" width="420px">
      <ElForm label-width="80px">
        <ElFormItem label="节点">
          <span>{{ editCategoryForm.nodeName }}</span>
        </ElFormItem>
        <ElFormItem label="当前类别">
          <span>{{ editCategoryForm.currentCategory }}</span>
        </ElFormItem>
        <ElFormItem label="新类别" required>
          <ElInput v-model="editCategoryForm.newCategory" placeholder="输入新类别名称" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editCategoryDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="handleEditCategory">确定</ElButton>
      </template>
    </ElDialog>

    <!-- ─── Edit Edge Dialog ─── -->
    <ElDialog v-model="editEdgeDialogVisible" title="编辑边" width="520px">
      <ElForm label-width="120px">
        <ElFormItem label="源节点" required>
          <ElInput v-model="editEdgeForm.source" placeholder="源节点名称" />
        </ElFormItem>
        <ElFormItem label="源节点类别">
          <ElInput v-model="editEdgeForm.source_category" placeholder="entity" />
        </ElFormItem>
        <ElFormItem label="关系" required>
          <ElInput v-model="editEdgeForm.relation" placeholder="关系类型" />
        </ElFormItem>
        <ElFormItem label="目标节点" required>
          <ElInput v-model="editEdgeForm.target" placeholder="目标节点名称" />
        </ElFormItem>
        <ElFormItem label="目标节点类别">
          <ElInput v-model="editEdgeForm.target_category" placeholder="entity" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="editEdgeDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="handleEditEdge">确定</ElButton>
      </template>
    </ElDialog>
</div>
</template>

<style scoped>
.triple-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  padding: 8px 0;
}

.file-selector {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.file-selector .label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.no-data-hint {
  margin-left: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.triple-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.graph-summary {
  flex-shrink: 0;
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.sep {
  margin: 0 8px;
}

.sub-tabs {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

.sub-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.sub-tabs :deep(.el-tab-pane) {
  height: 100%;
  overflow: hidden;
}

.toolbar {
  margin-top: 8px;
  flex-shrink: 0;
  margin-bottom: 8px;
}

.tab-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.tab-body .el-table {
  flex-shrink: 1;
  min-height: 0;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  padding: 8px 0;
}

.loading-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--el-text-color-secondary);
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
}
</style>
