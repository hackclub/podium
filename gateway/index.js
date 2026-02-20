import 'dotenv/config';
import http from 'node:http';
import httpProxy from 'http-proxy';

const GATEWAY_PORT = parseInt(process.env.GATEWAY_PORT || '3000', 10);
const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://127.0.0.1:8001';
const EVENTS_SERVICE_URL = process.env.EVENTS_SERVICE_URL || 'http://127.0.0.1:8002';
const PROJECTS_SERVICE_URL = process.env.PROJECTS_SERVICE_URL || 'http://127.0.0.1:8003';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';

const proxy = httpProxy.createProxyServer({});

proxy.on('error', (err, req, res) => {
  console.error(`[gateway] Proxy error: ${err.message} → ${req.url}`);
  if (!res.headersSent) {
    res.writeHead(502, { 'Content-Type': 'text/plain' });
    res.end('Gateway error – is the target server running?');
  }
});

function getTarget(url) {
  if (url.startsWith('/api/auth/') || url.startsWith('/api/users/') || url === '/api/users') {
    return AUTH_SERVICE_URL;
  }
  if (url.startsWith('/api/events/') || url === '/api/events') {
    return EVENTS_SERVICE_URL;
  }
  if (url.startsWith('/api/projects/') || url === '/api/projects') {
    return PROJECTS_SERVICE_URL;
  }
  return FRONTEND_URL;
}

const server = http.createServer((req, res) => {
  const url = req.url || '/';

  if (url === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end('{"status":"ok"}');
    return;
  }

  const target = getTarget(url);
  proxy.web(req, res, { target });
});

// Forward WebSocket upgrades (Vite HMR uses WebSockets)
server.on('upgrade', (req, socket, head) => {
  const url = req.url || '/';
  const target = getTarget(url);
  proxy.ws(req, socket, head, { target });
});

server.listen(GATEWAY_PORT, () => {
  console.log(`[gateway] Listening on http://localhost:${GATEWAY_PORT}`);
  console.log(`[gateway]   /api/auth/*     → ${AUTH_SERVICE_URL}`);
  console.log(`[gateway]   /api/users/*    → ${AUTH_SERVICE_URL}`);
  console.log(`[gateway]   /api/events/*   → ${EVENTS_SERVICE_URL}`);
  console.log(`[gateway]   /api/projects/* → ${PROJECTS_SERVICE_URL}`);
  console.log(`[gateway]   /*              → ${FRONTEND_URL}`);
});
