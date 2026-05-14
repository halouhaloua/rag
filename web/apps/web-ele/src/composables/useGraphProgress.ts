import { ref, onUnmounted } from 'vue';

import { useAccessStore } from '@vben/stores';

export interface ProgressEvent {
  stage: string;
  progress: number;
  message: string;
}

function getWsBaseUrl(): string {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/basic-api/rag/api/ws`;
}

function getAccessToken(): string {
  return useAccessStore().accessToken || '';
}

export function useGraphProgress() {
  const isConnecting = ref(false);
  const progress = ref(0);
  const stage = ref('');
  const message = ref('');
  const isComplete = ref(false);
  const hasError = ref(false);
  const showProgressDialog = ref(false);

  let ws: WebSocket | null = null;
  let clientId = '';

  function generateClientId(): string {
    return `web_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function connect(onProgress?: (evt: ProgressEvent) => void) {
    clientId = generateClientId();
    isConnecting.value = true;
    progress.value = 0;
    isComplete.value = false;
    hasError.value = false;

    const token = getAccessToken();
    const wsUrl = `${getWsBaseUrl()}/${clientId}?token=${encodeURIComponent(token)}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      isConnecting.value = false;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
          progress.value = data.progress;
          stage.value = data.stage;
          message.value = data.message;
          onProgress?.({ stage: data.stage, progress: data.progress, message: data.message });
        } else if (data.type === 'complete') {
          isComplete.value = true;
          message.value = data.message;
          onProgress?.({ stage: 'complete', progress: 100, message: data.message });
        } else if (data.type === 'error') {
          hasError.value = true;
          message.value = data.message;
        }
      } catch {
        // ignore
      }
    };

    ws.onerror = () => {
      hasError.value = true;
      isConnecting.value = false;
    };

    ws.onclose = () => {
      isConnecting.value = false;
    };
  }

  function disconnect() {
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  function reset() {
    progress.value = 0;
    stage.value = '';
    message.value = '';
    isComplete.value = false;
    hasError.value = false;
  }

  /**
   * Promise-based graph construction with WebSocket progress.
   * Opens a WS connection, sends the construct request, and resolves on 'complete' event.
   * Falls back to resolve after 30s timeout if WS stays open (defensive fallback).
   */
  function constructWithProgress(
    kbId: string,
    fileId: string,
    onProgress?: (msg: string, pct: number) => void,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const cid = generateClientId();
      const token = getAccessToken();
      const wsUrl = `${getWsBaseUrl()}/${cid}?token=${encodeURIComponent(token)}`;

      showProgressDialog.value = true;
      progress.value = 0;
      isComplete.value = false;
      hasError.value = false;

      const socket = new WebSocket(wsUrl);
      let hasResolved = false;

      const done = (err?: Error) => {
        if (hasResolved) return;
        hasResolved = true;
        socket.close();
        showProgressDialog.value = false;
        if (err) reject(err);
        else resolve();
      };

      socket.onopen = () => {
        // WS connected, send construct request
        fetch(`/basic-api/rag/api/knowledge-base/${kbId}/files/${fileId}/construct-graph?client_id=${cid}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        }).catch((err) => done(err));
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'progress') {
            progress.value = data.progress;
            message.value = data.message;
            onProgress?.(data.message, data.progress);
          } else if (data.type === 'complete') {
            isComplete.value = true;
            progress.value = 100;
            done();
          } else if (data.type === 'error') {
            done(new Error(data.message));
          }
        } catch {
          // ignore
        }
      };

      socket.onerror = () => done(new Error('WebSocket 连接失败'));

      // 30s timeout fallback
      setTimeout(() => {
        if (socket.readyState === WebSocket.OPEN && !hasResolved) {
          done();
        }
      }, 30000);
    });
  }

  onUnmounted(() => {
    disconnect();
  });

  return {
    clientId: () => clientId,
    isConnecting,
    progress,
    stage,
    message,
    isComplete,
    hasError,
    showProgressDialog,
    connect,
    disconnect,
    reset,
    constructWithProgress,
  };
}
