import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { once } from 'node:events';
import { request } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { createApp } from '../src/server.js';
import { createReplayVision } from '../src/vision.js';
import { sampleForm } from '../test-support/samples.js';

test('the browser assets and full demo API work over a real HTTP connection', async () => {
  const name = 'jalnetra-' + randomUUID();
  const socketPath = process.platform === 'win32' ? '\\\\.\\pipe\\' + name : join(tmpdir(), name);
  const server = createApp({ rehearsal: true, vision: createReplayVision() });
  server.listen(socketPath);
  await once(server, 'listening');
  async function send(path, method = 'GET', body) {
    const message = new Request('http://localhost' + path, { method, body });
    const bytes = Buffer.from(await message.arrayBuffer());
    return new Promise((resolve, reject) => {
      const requestHeaders = { Host: 'localhost', ...Object.fromEntries(message.headers) };
      if (bytes.length) requestHeaders['Content-Length'] = String(bytes.length);
      const call = request({ socketPath, path, method, headers: requestHeaders }, response => {
        const chunks = [];
        response.on('data', chunk => chunks.push(chunk));
        response.once('error', reject);
        response.once('end', () => resolve({
          status: response.statusCode, headers: response.headers, body: Buffer.concat(chunks),
        }));
      });
      call.once('error', reject);
      call.end(bytes);
    });
  }
  // JSON routes require a JSON Content-Type rather than the default string type.
  const json = value => new Blob([JSON.stringify(value)], { type: 'application/json' });
  try {
    const page = await send('/');
    assert.equal(page.status, 200);
    assert.match(page.body.toString(), /draft-dialog/);
    assert.match(page.headers['content-security-policy'], /default-src 'self'/);
    for (const asset of ['/app.js', '/style.css']) assert.equal((await send(asset)).status, 200);

    const setup = await send('/api/demo/reset', 'POST', json({}));
    assert.equal(setup.status, 200);
    const addition = await send('/api/reports', 'POST', sampleForm('foam-bank'));
    assert.equal(addition.status, 201);
    const report = JSON.parse(addition.body);
    const image = await send(report.photoUrl);
    assert.equal(image.headers['content-type'], 'image/png');
    const map = JSON.parse((await send('/api/hotspots')).body);
    assert.equal(map.zones[0].status, 'priority_hotspot');

    const draftResponse = await send('/api/complaints', 'POST', json({ zoneId: 'north-inlet', category: 'foam' }));
    assert.equal(draftResponse.status, 201);
    const draft = JSON.parse(draftResponse.body);
    const download = await send('/api/complaints/' + draft.id + '/export');
    assert.match(download.headers['content-disposition'], /^attachment/);
    assert.match(download.body.toString(), /DEMO DRAFT/);
    assert.ok(download.body.toString().includes(report.id));
  } finally {
    await new Promise(resolve => server.close(resolve));
  }
});
