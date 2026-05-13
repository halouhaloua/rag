const WS_BASE = '/basic-api';

export function createWebSocket(path: string, clientId?: string): WebSocket {
  const id = clientId || `web_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const url = `${protocol}//${location.host}${WS_BASE}${path}${path.includes('?') ? '&' : '?'}client_id=${id}`;
  return new WebSocket(url);
}
