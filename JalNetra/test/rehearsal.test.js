import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createReplayVision } from '../src/vision.js';
import { openApp, postJson } from '../test-support/http.js';
import { submitSample } from '../test-support/samples.js';

test('rehearsal completes the full demo and resets only its in-memory dataset', async () => {
  const vision = createReplayVision();
  const ordinary = openApp(':memory:', { vision });
  const rehearsal = openApp(':memory:', { vision, rehearsal: true });
  try {
    const retained = await submitSample(ordinary, 'algae');
    assert.equal((await postJson(ordinary, '/api/demo/reset', {})).status, 404);

    const reset = () => postJson(rehearsal, '/api/demo/reset', {}).then(response => response.json());
    const dashboard = () => rehearsal.request('/api/hotspots').then(response => response.json());
    const first = await reset();
    assert.ok(first.seededReportId);
    assert.equal((await dashboard()).zones[0].status, 'watch');
    const photo = await submitSample(rehearsal, 'foam-bank');
    const beforeReview = (await dashboard()).zones[0].categories[0];
    assert.equal(beforeReview.status, 'priority_hotspot');
    assert.deepEqual(new Set(beforeReview.evidenceReportIds), new Set([first.seededReportId, photo.id]));
    const draft = await postJson(rehearsal, '/api/complaints', {
      zoneId: 'north-inlet', category: 'foam',
    }).then(response => response.json());
    const unclear = await submitSample(rehearsal, 'unclear');
    assert.equal(unclear.status, 'needs_review');
    assert.equal((await dashboard()).zones[0].categories[0].evidenceCount, 2);
    assert.match(await rehearsal.request('/api/complaints/' + draft.id + '/export').then(response => response.text()),
      /DEMO DRAFT/);

    const next = await reset();
    assert.notEqual(next.seededReportId, first.seededReportId);
    assert.equal((await dashboard()).zones[0].status, 'watch');
    assert.equal((await rehearsal.request('/api/reports').then(response => response.json())).length, 1);
    assert.equal((await rehearsal.request('/api/complaints/' + draft.id)).status, 404);
    assert.equal((await ordinary.request('/api/reports/' + retained.id)).status, 200);
  } finally {
    ordinary.close();
    rehearsal.close();
  }
});

test('live observations are kept separate and offline sample routes are disabled in live mode', async () => {
  const { mkdtemp, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const directory = await mkdtemp(join(tmpdir(), 'jalnetra-modes-'));
  const db = join(directory, 'modes.sqlite');
  const offline = openApp(db, { vision: createReplayVision() });
  const live = openApp(db, {
    vision: {
      source: 'live_model',
      async analyse() {
        return { imageQuality: 'usable', detections: [{ category: 'foam', cue: 'Provider test result' }] };
      },
    },
  });
  try {
    const demo = await submitSample(offline, 'foam-inlet');
    const real = await submitSample(live, 'foam-bank');
    assert.equal(real.dataMode, 'live');
    assert.equal((await live.request('/api/reports/' + demo.id)).status, 404);
    assert.equal((await offline.request('/api/reports/' + real.id)).status, 404);
    assert.equal((await live.request('/api/demo/samples/foam-inlet')).status, 404);
    assert.equal((await postJson(live, '/api/demo/reset', {})).status, 404);
    const liveMap = await live.request('/api/hotspots').then(response => response.json());
    assert.deepEqual(liveMap.zones[0].categories[0].evidenceReportIds, [real.id]);
  } finally {
    live.close();
    offline.close();
    await rm(directory, { recursive: true, force: true });
  }
});
