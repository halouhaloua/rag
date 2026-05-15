import { requestClient } from '#/api/request';
import { streamRequestClient } from '#/api/stream-request';
import { useAccessStore } from '@vben/stores';

// ─── Types ───
export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  kb_type: string;
  file_count: number;
  sys_create_datetime: string;
  sys_update_datetime: string;
}

export interface KnowledgeBaseListResult {
  items: KnowledgeBase[];
  total: number;
}

export interface KnowledgeBaseFile {
  id: string;
  kb_id: string;
  filename: string;
  file_type?: string;
  file_size: number;
  has_graph: boolean;
  schema_json?: Record<string, any>;
  sys_create_datetime: string;
}

export interface KnowledgeBaseFileListResult {
  items: KnowledgeBaseFile[];
  total: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  categories: GraphCategory[];
  stats: GraphStats;
}

export interface GraphNode {
  id: string;
  name: string;
  category: string;
  symbolSize?: number;
  properties?: Record<string, any>;
}

export interface GraphLink {
  source: string;
  target: string;
  name: string;
  value?: number;
}

export interface GraphCategory {
  name: string;
  itemStyle?: Record<string, any>;
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  displayed_nodes?: number;
  displayed_edges?: number;
}

export interface IRCoTConfig {
  enable_ircot: boolean;
  max_steps: number;
}

export interface ChatConversation {
  id: string;
  title: string;
  user_id: string;
  model_name?: string;
  sys_create_datetime: string;
  sys_update_datetime: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  model_name?: string;
  sys_create_datetime: string;
}

export interface QuestionResult {
  answer: string;
  sub_questions: any[];
  retrieved_triples: string[];
  retrieved_chunks: string[];
  reasoning_steps: any[];
  visualization_data: Record<string, any>;
}

// ─── Knowledge Base CRUD ───
export async function getKnowledgeBaseListApi(params?: {
  page?: number;
  pageSize?: number;
  name?: string;
}) {
  return requestClient.get<KnowledgeBaseListResult>(
    '/rag/api/knowledge-bases',
    { params },
  );
}

export async function getKnowledgeBaseDetailApi(kbId: string) {
  return requestClient.get<KnowledgeBase>(
    `/rag/api/knowledge-base/${kbId}`,
  );
}

export async function createKnowledgeBaseApi(data: {
  name: string;
  description?: string;
}) {
  return requestClient.post<KnowledgeBase>('/rag/api/knowledge-base', data);
}

export async function updateKnowledgeBaseApi(
  kbId: string,
  data: { name?: string; description?: string },
) {
  return requestClient.put<KnowledgeBase>(
    `/rag/api/knowledge-base/${kbId}`,
    data,
  );
}

export async function deleteKnowledgeBaseApi(kbId: string) {
  return requestClient.delete(`/rag/api/knowledge-base/${kbId}`);
}

// ─── File Management ───
export async function uploadFilesApi(
  kbId: string,
  files: File[],
  schemaFile?: File | null,
) {
  const formData = new FormData();
  files.forEach((f) => formData.append('files', f));
  if (schemaFile) {
    formData.append('schema_file', schemaFile);
  }
  return requestClient.post(
    `/rag/api/knowledge-base/${kbId}/files/upload`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
}

export async function getFileListApi(kbId: string) {
  return requestClient.get<KnowledgeBaseFileListResult>(
    `/rag/api/knowledge-base/${kbId}/files`,
  );
}

export async function getFileDetailApi(kbId: string, fileId: string) {
  return requestClient.get<KnowledgeBaseFile>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}`,
  );
}

export async function deleteFileApi(kbId: string, fileId: string) {
  return requestClient.delete(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}`,
  );
}

export async function updateFileSchemaApi(
  kbId: string,
  fileId: string,
  schema: Record<string, any>,
) {
  return requestClient.put(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/schema`,
    { schema },
  );
}

// ─── Graph Operations ───
export async function constructGraphApi(
  kbId: string,
  fileId: string,
  clientId?: string,
) {
  const params: Record<string, any> = {};
  if (clientId) params.client_id = clientId;
  return requestClient.post(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/construct-graph`,
    {},
    { params },
  );
}

export async function getGraphDataApi(kbId: string, fileId: string) {
  return requestClient.get<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph`,
  );
}

export interface PaginatedGraphItems<T> {
  items: T[];
  total: number;
}

export async function getGraphNodesApi(
  kbId: string,
  fileId: string,
  page: number,
  pageSize: number,
) {
  return requestClient.get<PaginatedGraphItems<GraphNode>>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/nodes`,
    { params: { page, pageSize } },
  );
}

export async function getGraphEdgesApi(
  kbId: string,
  fileId: string,
  page: number,
  pageSize: number,
) {
  return requestClient.get<PaginatedGraphItems<GraphLink>>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/edges`,
    { params: { page, pageSize } },
  );
}

export async function reconstructGraphApi(
  kbId: string,
  fileId: string,
  clientId?: string,
) {
  const params: Record<string, any> = {};
  if (clientId) params.client_id = clientId;
  return requestClient.post(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/reconstruct`,
    {},
    { params },
  );
}

// ─── Question Answering (SSE) ───
export async function askQuestionStream(
  kbId: string,
  fileId: string,
  question: string,
  clientId: string,
  callbacks?: {
    onToken?: (token: string) => void;
    onReasoningToken?: (token: string) => void;
    onMetadata?: (data: any) => void;
    onReasoningSteps?: (data: any) => void;
    onVisualization?: (data: any) => void;
    onDone?: (data: any) => void;
    onStatus?: (progress: number, message: string) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
  },
): Promise<QuestionResult> {
  const body = { question, file_id: fileId };
  const params = new URLSearchParams({ client_id: clientId });

  const answerParts: string[] = [];
  let subQuestions: any[] = [];
  let triples: string[] = [];
  let chunks: string[] = [];
  let reasoningSteps: any[] = [];
  let visualizationData: Record<string, any> = {};

  return new Promise((resolve, reject) => {
    streamRequestClient(
      `/rag/api/knowledge-base/${kbId}/files/${fileId}/ask-question?${params}`,
      body,
      {
        onData: (data: any) => {
          if (!['token', 'metadata', 'reasoning_steps', 'visualization', 'done', 'status', 'error', 'answer_start', 'answer_end', 'reasoning_start', 'reasoning_end', 'ircot_start', 'ircot_end', 'answer_found'].includes(data.type)) return;
          switch (data.type) {
            case 'token':
              if (data.phase === 'reasoning') {
                callbacks?.onReasoningToken?.(data.text);
              } else {
                answerParts.push(data.text);
                callbacks?.onToken?.(data.text);
              }
              break;
            case 'metadata':
              subQuestions = data.sub_questions || [];
              triples = data.triples || [];
              chunks = data.chunks || [];
              callbacks?.onMetadata?.(data);
              break;
            case 'reasoning_steps':
              reasoningSteps = data.data?.reasoning_steps || [];
              callbacks?.onReasoningSteps?.(data.data);
              break;
            case 'visualization':
              visualizationData = data.data || {};
              callbacks?.onVisualization?.(data.data);
              break;
            case 'done':
              callbacks?.onDone?.(data);
              resolve({
                answer: data.answer || answerParts.join(''),
                sub_questions: subQuestions,
                retrieved_triples: triples,
                retrieved_chunks: chunks,
                reasoning_steps: reasoningSteps,
                visualization_data: visualizationData,
              });
              break;
            case 'answer_found':
              if (data.answer) {
                answerParts.push(data.answer);
                callbacks?.onToken?.(data.answer);
              }
              break;
            case 'status':
              callbacks?.onStatus?.(data.progress, data.message);
              break;
            case 'error':
              callbacks?.onError?.(new Error(data.message));
              reject(new Error(data.message));
              break;
          }
        },
        onError: (err) => {
          callbacks?.onError?.(err);
          reject(err);
        },
        onComplete: () => callbacks?.onComplete?.(),
      },
    );
  });
}

// ─── IRCoT Config ───
export async function getIRCoTStatusApi() {
  return requestClient.get<IRCoTConfig>('/rag/api/config/ircot');
}

export async function setIRCoTEnabledApi(enable: boolean) {
  return requestClient.post('/rag/api/config/ircot', { enable });
}

// ─── Chat / Conversation API ───
export async function createConversationApi(data: {
  user_id: string;
  title?: string;
  model_name?: string;
}) {
  return requestClient.post<ChatConversation>(
    '/rag/chat/conversation/create',
    data,
  );
}

export async function getUserConversationsApi(
  userId: string,
  page?: number,
  pageSize?: number,
) {
  const params: Record<string, any> = {};
  if (page) params.page = page;
  if (pageSize) params.pageSize = pageSize;
  return requestClient.get<ChatConversation[]>(
    `/rag/chat/conversations/${userId}`,
    { params },
  );
}

export async function getChatHistoryApi(conversationId: string) {
  return requestClient.get<ChatMessage[]>(
    `/rag/chat/history/${conversationId}`,
  );
}

export async function deleteConversationApi(conversationId: string) {
  return requestClient.delete(
    `/rag/chat/conversation/${conversationId}`,
  );
}

export async function chatCompletionStream(
  data: {
    user_id: string;
    conversation_id?: string;
    question: string;
    model_name?: string;
    file_id: string;
  },
  callbacks?: {
    onToken?: (token: string) => void;
    onReasoningToken?: (token: string) => void;
    onMetadata?: (data: any) => void;
    onReasoningSteps?: (data: any) => void;
    onVisualization?: (data: any) => void;
    onDone?: (data: any) => void;
    onStatus?: (progress: number, message: string) => void;
    onError?: (error: Error) => void;
    onComplete?: () => void;
  },
): Promise<QuestionResult> {
  const answerParts: string[] = [];
  let subQuestions: any[] = [];
  let triples: string[] = [];
  let chunks: string[] = [];
  let reasoningSteps: any[] = [];
  let visualizationData: Record<string, any> = {};

  return new Promise((resolve, reject) => {
    streamRequestClient(
      '/rag/chat/message/chat',
      data,
      {
        onData: (data: any) => {
          if (!['token', 'metadata', 'reasoning_steps', 'visualization', 'done', 'status', 'error', 'answer_start', 'answer_end', 'reasoning_start', 'reasoning_end', 'ircot_start', 'ircot_end', 'answer_found'].includes(data.type)) return;
          switch (data.type) {
            case 'token':
              if (data.phase === 'reasoning') {
                callbacks?.onReasoningToken?.(data.text);
              } else {
                answerParts.push(data.text);
                callbacks?.onToken?.(data.text);
              }
              break;
            case 'metadata':
              subQuestions = data.sub_questions || [];
              triples = data.triples || [];
              chunks = data.chunks || [];
              callbacks?.onMetadata?.(data);
              break;
            case 'reasoning_steps':
              reasoningSteps = data.data?.reasoning_steps || [];
              callbacks?.onReasoningSteps?.(data.data);
              break;
            case 'visualization':
              visualizationData = data.data || {};
              callbacks?.onVisualization?.(data.data);
              break;
            case 'done':
              callbacks?.onDone?.(data);
              resolve({
                answer: data.answer || answerParts.join(''),
                sub_questions: subQuestions,
                retrieved_triples: triples,
                retrieved_chunks: chunks,
                reasoning_steps: reasoningSteps,
                visualization_data: visualizationData,
              });
              break;
            case 'answer_found':
              if (data.answer) {
                answerParts.push(data.answer);
                callbacks?.onToken?.(data.answer);
              }
              break;
            case 'status':
              callbacks?.onStatus?.(data.progress, data.message);
              break;
            case 'error':
              callbacks?.onError?.(new Error(data.message));
              reject(new Error(data.message));
              break;
          }
        },
        onError: (err) => {
          callbacks?.onError?.(err);
          reject(err);
        },
        onComplete: () => callbacks?.onComplete?.(),
      },
    );
  });
}

// ─── Triple Management ───
export async function updateNodeCategoryApi(
  kbId: string,
  fileId: string,
  nodeName: string,
  newCategory: string,
) {
  return requestClient.put<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/node/category`,
    { node_name: nodeName, new_category: newCategory },
  );
}

export async function addGraphEdgesApi(
  kbId: string,
  fileId: string,
  edges: {
    source: string;
    relation: string;
    target: string;
    source_category?: string;
    target_category?: string;
  }[],
) {
  return requestClient.post<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/edges`,
    { edges },
  );
}

export async function addGraphNodesApi(
  kbId: string,
  fileId: string,
  nodes: { name: string; category?: string }[],
) {
  return requestClient.post<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/nodes`,
    { nodes },
  );
}

export async function deleteGraphNodeApi(
  kbId: string,
  fileId: string,
  nodeName: string,
) {
  return requestClient.delete<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/nodes/${encodeURIComponent(nodeName)}`,
  );
}

export async function deleteGraphEdgeApi(
  kbId: string,
  fileId: string,
  source: string,
  relation: string,
  target: string,
) {
  return requestClient.delete<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/edge`,
    { data: { source, relation, target } },
  );
}

export interface GraphEdgeUpdatePayload {
  source: string;
  relation: string;
  target: string;
  new_source?: string;
  new_relation?: string;
  new_target?: string;
  new_source_category?: string;
  new_target_category?: string;
}

export async function updateGraphEdgeApi(
  kbId: string,
  fileId: string,
  data: GraphEdgeUpdatePayload,
) {
  return requestClient.put<GraphData>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/graph/edge`,
    data,
  );
}

// ─── KB Permission Management ───
export async function getRoleKbPermissionsApi(roleId: string) {
  return requestClient.get<KnowledgeBaseListResult>(
    `/rag/api/knowledge-base/role/${roleId}/kb-permissions`,
  );
}

export async function updateRoleKbPermissionsApi(
  roleId: string,
  kbIds: string[],
) {
  return requestClient.put(
    `/rag/api/knowledge-base/role/${roleId}/kb-permissions`,
    { kb_ids: kbIds },
  );
}

// ─── File Preview ───
export function getKbFilePreviewUrl(kbId: string, fileId: string): string {
  const accessStore = useAccessStore();
  return `/basic-api/rag/api/knowledge-base/${kbId}/files/${fileId}/preview?token=${accessStore.accessToken}`;
}

export async function getKbFilePreviewBlob(kbId: string, fileId: string): Promise<Blob> {
  const accessStore = useAccessStore();
  const token = accessStore.accessToken;
  const resp = await fetch(
    `/basic-api/rag/api/knowledge-base/${kbId}/files/${fileId}/preview?token=${token}`,
  );
  return resp.blob();
}

export async function getKbFileContentApi(kbId: string, fileId: string) {
  return requestClient.get<{ content: string; filename: string }>(
    `/rag/api/knowledge-base/${kbId}/files/${fileId}/content`,
  );
}

// ─── Status ───
export async function getRagStatusApi() {
  return requestClient.get('/rag/api/status');
}
