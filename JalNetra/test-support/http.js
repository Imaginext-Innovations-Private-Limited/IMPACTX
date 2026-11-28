import { Readable } from 'node:stream';
import { createApp } from '../src/server.js';

export function formFor(observedAt, changes = {}, pixels = Uint8Array.of(20, 50, 80, 200, 230, 255)) {
  const form = new FormData();
  const fields = {
    requestId: 'test-intake-001',
    zoneId: 'north-inlet',
    observedAt,
    photoWidth: '2',
    photoHeight: '1',
    ph: '7.2',
    ...changes,
  };
  for (const [key, value] of Object.entries(fields)) form.set(key, value);
  form.set('photo', new Blob([pixels], {
    type: 'application/octet-stream',
  }), 'fixture.rgb');
  return form;
}

export function openApp(dbPath = ':memory:', options = {}) {
  const server = createApp({ dbPath, ...options });
  const handle = server.listeners('request')[0];
  async function request(url, options = {}) {
    const input = new Request('http://127.0.0.1' + url, options);
    const body = Buffer.from(await input.arrayBuffer());
    const req = Object.assign(Readable.from(body.length ? [body] : []), {
      method: input.method,
      url,
      headers: { host: '127.0.0.1', ...Object.fromEntries(input.headers) },
    });
    return new Promise((resolve, reject) => {
      const res = {
        headers: {},
        setHeader(name, value) {
          this.headers[name] = value;
        },
        writeHead(status, headers) {
          this.status = status;
          Object.assign(this.headers, headers);
        },
        end(data) {
          resolve(new Response(data, { status: this.status, headers: this.headers }));
        },
      };
      handle(req, res).catch(reject);
    });
  }
  return { request, close: () => server.emit('close') };
}

export function postJson(app, path, data) {
  return app.request(path, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
  });
}
