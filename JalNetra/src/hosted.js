import { randomBytes } from 'node:crypto';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Readable } from 'node:stream';
import { createApp } from './server.js';
import { createReplayVision } from './vision.js';

const cookieName = '__Host-jalnetra';
const maxSnapshotBytes = 12 * 1024 * 1024;
const sevenDays = 7 * 24 * 60 * 60;
const readOnlyWithoutState = new Set(['/api/status', '/api/zones', '/api/lakes']);

export class SnapshotConflict extends Error {}

function getSession(request) {
  const cookie = request.headers.get('cookie')?.split(';').map(value => value.trim())
    .find(value => value.startsWith(cookieName + '='));
  const token = cookie?.slice(cookieName.length + 1);
  return /^[a-f0-9]{64}$/.test(token ?? '') ? token : null;
}

function issueCookie(response, token) {
  response.headers.append('Set-Cookie',
    cookieName + '=' + token + '; Path=/; Max-Age=' + sevenDays + '; Secure; HttpOnly; SameSite=Strict');
}

function errorResponse(status, code, message) {
  return Response.json({ error: { code, message } }, {
    status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' },
  });
}

async function dispatch(request, path, origin, dbPath, vision) {
  const app = createApp({ dbPath, rehearsal: true, hostedOrigin: origin, vision });
  const input = Object.assign(request.body ? Readable.fromWeb(request.body) : Readable.from([]), {
    url: path, method: request.method, headers: Object.fromEntries(request.headers),
  });
  let result;
  const output = {
    status: 500,
    headers: new Headers(),
    setHeader(name, value) { this.headers.set(name, value); },
    writeHead(status, headers) {
      this.status = status;
      for (const [name, value] of Object.entries(headers)) this.headers.set(name, value);
    },
    end(body) { result = new Response(body, { status: this.status, headers: this.headers }); },
  };
  try {
    await app.listeners('request')[0](input, output);
    return result;
  } finally {
    app.emit('close');
  }
}

export function createHostedHandler(store) {
  const vision = createReplayVision();
  return async function handle(request) {
    const url = new URL(request.url);
    const rewritten = url.pathname === '/api/jalnetra';
    const route = rewritten ? url.searchParams.get('jalroute') : url.pathname.slice(5);
    if (!/^(?:status|lakes|zones|hotspots|reports|readings|concerns|complaints|demo)(?:\/[a-zA-Z0-9_-]+)*$/.test(route ?? '')) {
      return errorResponse(404, 'NOT_FOUND', 'This page could not be found.');
    }
    const path = '/api/' + route;
    const params = new URLSearchParams(url.searchParams);
    params.delete('jalroute');
    const query = params.size ? '?' + params.toString() : '';
    const write = ['POST', 'PATCH'].includes(request.method);
    if (write && request.headers.get('origin') !== url.origin) {
      return errorResponse(403, 'INVALID_ORIGIN', 'Open the demo directly to make changes.');
    }
    const token = getSession(request);
    if (write && !token) {
      return errorResponse(403, 'DEMO_SESSION_REQUIRED', 'Reload the demo and allow its session cookie.');
    }

    let directory;
    try {
      if (!write && (readOnlyWithoutState.has(path) || path.startsWith('/api/demo/samples/'))) {
        const response = await dispatch(request, path + query, url.origin, ':memory:', vision);
        if (path === '/api/status' && !token) issueCookie(response, randomBytes(32).toString('hex'));
        return response;
      }

      const blobPath = 'sessions/' + token + '.sqlite';
      const snapshot = token ? await store.read(blobPath, { forWrite: write }) : null;
      if (!write && !snapshot) return await dispatch(request, path + query, url.origin, ':memory:', vision);

      directory = await mkdtemp(join(tmpdir(), 'jalnetra-host-'));
      const dbPath = join(directory, 'session.sqlite');
      if (snapshot) await writeFile(dbPath, snapshot.bytes);

      const response = await dispatch(request, path + query, url.origin, dbPath, vision);
      if (write && response.ok) {
        const bytes = await readFile(dbPath);
        if (bytes.byteLength > maxSnapshotBytes) {
          return errorResponse(413, 'DEMO_STORAGE_FULL', 'This demo session is full. Restart the rehearsal and try again.');
        }
        await store.write(blobPath, bytes, snapshot?.etag);
      }
      return response;
    } catch (error) {
      if (error instanceof SnapshotConflict) {
        return errorResponse(409, 'SESSION_CONFLICT', 'The session changed in another request. Try the action again.');
      }
      console.error('JalNetra hosted storage failed:', error.name);
      return errorResponse(503, 'DEMO_STORAGE_UNAVAILABLE', 'Demo storage is temporarily unavailable.');
    } finally {
      if (directory) await rm(directory, { recursive: true, force: true });
    }
  };
}
