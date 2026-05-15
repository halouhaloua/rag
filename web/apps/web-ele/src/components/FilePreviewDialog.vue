<script setup lang="ts">
import { ref } from 'vue';
import { ElDialog } from 'element-plus';
import { getFileStreamUrl, getFileStream } from '#/api/core/file';
import * as mammoth from 'mammoth';

const visible = ref(false);
const loading = ref(false);
const error = ref('');
const fileId = ref('');
const filename = ref('');
const fileExt = ref('');
const previewUrl = ref('');
const htmlContent = ref('');
const textContent = ref('');

let customPreviewUrl: string | undefined;
let customFetchBlob: (() => Promise<Blob>) | undefined;

type PreviewType = 'iframe' | 'html' | 'text' | 'image' | 'video' | 'audio' | 'unsupported';
const previewType = ref<PreviewType>('unsupported');

const fileTypeMap: Record<string, PreviewType> = {
  pdf: 'iframe',
  docx: 'html',
  txt: 'text',
  md: 'text',
  json: 'text',
  xml: 'text',
  yaml: 'text',
  yml: 'text',
  csv: 'text',
  log: 'text',
  ini: 'text',
  cfg: 'text',
  py: 'text',
  js: 'text',
  ts: 'text',
  jsx: 'text',
  tsx: 'text',
  html: 'text',
  css: 'text',
  scss: 'text',
  less: 'text',
  java: 'text',
  cpp: 'text',
  c: 'text',
  h: 'text',
  sql: 'text',
  sh: 'text',
  bat: 'text',
  ps1: 'text',
  env: 'text',
  gitignore: 'text',
  dockerfile: 'text',
  png: 'image',
  jpg: 'image',
  jpeg: 'image',
  gif: 'image',
  svg: 'image',
  bmp: 'image',
  webp: 'image',
  ico: 'image',
  mp4: 'video',
  webm: 'video',
  ogg: 'video',
  mov: 'video',
  avi: 'video',
  mkv: 'video',
  mp3: 'audio',
  wav: 'audio',
  flac: 'audio',
  aac: 'audio',
};

function getExt() {
  return (fileExt.value || '').toLowerCase().replace(/^\./, '');
}

function resolvePreviewType(): PreviewType {
  const ext = getExt();
  return fileTypeMap[ext] || 'unsupported';
}

async function loadPreview() {
  loading.value = true;
  error.value = '';
  previewType.value = resolvePreviewType();

  try {
    switch (previewType.value) {
      case 'iframe':
      case 'image':
      case 'video':
      case 'audio':
        previewUrl.value = customPreviewUrl || getFileStreamUrl(fileId.value);
        break;
      case 'html': {
        const blob = customFetchBlob
          ? await customFetchBlob()
          : (() => {
              const res: any = getFileStream(fileId.value);
              return res instanceof Blob ? res : (res as any)?.data;
            })();
        const arrayBuffer = await blob.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer });
        htmlContent.value = result.value;
        break;
      }
      case 'text': {
        const blob = customFetchBlob
          ? await customFetchBlob()
          : (() => {
              const res: any = getFileStream(fileId.value);
              return res instanceof Blob ? res : (res as any)?.data;
            })();
        textContent.value = await blob.text();
        break;
      }
      default:
        break;
    }
  } catch (err: any) {
    error.value = err?.message || '预览加载失败';
  } finally {
    loading.value = false;
  }
}

interface OpenOptions {
  id?: string;
  name?: string;
  file_ext?: string;
  previewUrl?: string;
  fetchBlob?: () => Promise<Blob>;
}

function open(options: OpenOptions) {
  fileId.value = options.id || '';
  filename.value = options.name || '';
  fileExt.value = options.file_ext || '';
  customPreviewUrl = options.previewUrl;
  customFetchBlob = options.fetchBlob;
  visible.value = true;
  loadPreview();
}

function close() {
  visible.value = false;
  htmlContent.value = '';
  textContent.value = '';
  previewUrl.value = '';
  error.value = '';
  customPreviewUrl = undefined;
  customFetchBlob = undefined;
}

defineExpose({ open });
</script>

<template>
  <ElDialog
    v-model="visible"
    :title="filename || '文件预览'"
    :close-on-click-modal="false"
    width="90vw"
    top="3vh"
    @close="close"
  >
    <div class="preview-body">
      <div v-if="loading" class="preview-loading">
        <span>加载中...</span>
      </div>
      <div v-else-if="error" class="preview-error">
        <p>{{ error }}</p>
      </div>
      <template v-else>
        <iframe
          v-if="previewType === 'iframe'"
          :src="previewUrl"
          class="preview-iframe"
        />
        <div
          v-if="previewType === 'html'"
          class="preview-html"
          v-html="htmlContent"
        />
        <pre
          v-if="previewType === 'text'"
          class="preview-text"
        >{{ textContent }}</pre>
        <img
          v-if="previewType === 'image'"
          :src="previewUrl"
          class="preview-image"
          alt="preview"
        />
        <video
          v-if="previewType === 'video'"
          :src="previewUrl"
          class="preview-media"
          controls
        />
        <audio
          v-if="previewType === 'audio'"
          :src="previewUrl"
          class="preview-audio"
          controls
        />
        <div
          v-if="previewType === 'unsupported'"
          class="preview-unsupported"
        >
          暂不支持预览该文件类型
        </div>
      </template>
    </div>
  </ElDialog>
</template>

<style scoped>
.preview-body {
  min-height: 85vh;
  display: flex;
  flex-direction: column;
}

.preview-loading,
.preview-error,
.preview-unsupported {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.preview-iframe {
  flex: 1;
  width: 100%;
  min-height: 85vh;
  border: none;
}

.preview-html {
  flex: 1;
  padding: 16px;
  overflow: auto;
  line-height: 1.6;
}

.preview-text {
  flex: 1;
  margin: 0;
  padding: 16px;
  overflow: auto;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.preview-image {
  max-width: 100%;
  max-height: 85vh;
  object-fit: contain;
  margin: 0 auto;
}

.preview-media {
  max-width: 100%;
  max-height: 85vh;
  margin: 0 auto;
}

.preview-audio {
  width: 100%;
  margin-top: 40px;
}
</style>
