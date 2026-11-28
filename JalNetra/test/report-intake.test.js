import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { inflateSync } from 'node:zlib';
import { formFor, openApp } from '../test-support/http.js';



test('observations are validated, idempotent and persisted with a readable photo', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'jalnetra-test-'));
  const dbPath = join(directory, 'reports.sqlite');
  let app = openApp(dbPath);
  try {
    const zones = await app.request('/api/zones').then(response => response.json());
    assert.deepEqual(zones.map(zone => zone.name), ['North Inlet', 'East Shore', 'South Bank']);
    assert.match(await app.request('/').then(response => response.text()), /Save observation/);
    const observedAt = new Date(Date.now() - 30000).toISOString();
    const submit = changes => app.request('/api/reports', { method: 'POST', body: formFor(observedAt, changes) });
    const blocked = await app.request('/api/reports', {
      method: 'POST',
      headers: { Origin: 'https://example.com' },
      body: formFor(observedAt),
    });
    assert.equal(blocked.status, 403);
    assert.equal((await submit({ zoneId: 'invalid' })).status, 400);
    assert.equal((await submit({ photoWidth: '3' })).status, 400);
    assert.equal((await submit({ ph: 'invalid' })).status, 400);
    assert.equal((await submit({ observedAt: '2031-02-30T00:00:00Z' })).status, 400);

    const responses = await Promise.all([submit(), submit()]);
    assert.deepEqual(responses.map(response => response.status).sort(), [200, 201]);
    const [saved, duplicate] = await Promise.all(responses.map(response => response.json()));
    assert.equal(saved.id, duplicate.id);
    assert.equal(saved.status, 'pending');
    assert.equal(saved.ph, 7.2);
    assert.equal((await submit({ note: 'Different payload' })).status, 409);
    assert.equal((await app.request('/api/reports?zoneId=east-shore').then(response => response.json())).length, 0);

    await app.close();
    app = null;
    app = openApp(dbPath);
    const recent = await app.request('/api/reports').then(response => response.json());
    assert.deepEqual(recent.map(report => report.id), [saved.id]);
    const photo = await app.request(saved.photoUrl);
    assert.equal(photo.headers.get('content-type'), 'image/png');
    const png = Buffer.from(await photo.arrayBuffer());
    assert.equal(png.subarray(1, 4).toString('ascii'), 'PNG');
    assert.equal(png.readUInt32BE(16), 2);
    assert.equal(png.readUInt32BE(20), 1);
    assert.equal(png.subarray(37, 41).toString('ascii'), 'IDAT');
    assert.deepEqual([...inflateSync(png.subarray(41, 41 + png.readUInt32BE(33)))], [0, 20, 50, 80, 200, 230, 255]);
  } finally {
    await app?.close();
    await rm(directory, { recursive: true, force: true });
  }
});

