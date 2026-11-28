import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createReplayVision } from '../src/vision.js';
import { openApp } from '../test-support/http.js';
import { submitSample } from '../test-support/samples.js';

test('hotspots count distinct recent photos for each zone and category', async () => {
  const app = openApp(':memory:', { vision: createReplayVision() });
  const dashboard = async () => (await app.request('/api/hotspots').then(response => response.json())).zones;
  try {
    assert.equal((await dashboard())[0].status, 'none');
    await submitSample(app, 'foam-inlet');
    assert.equal((await dashboard())[0].status, 'watch');
    const newer = await submitSample(app, 'foam-inlet', {
      requestId: 'same-photo-new-report', observedAt: new Date(Date.now() - 500).toISOString(),
    });
    assert.equal((await dashboard())[0].categories[0].evidenceCount, 1);
    assert.deepEqual((await dashboard())[0].categories[0].evidenceReportIds, [newer.id]);

    const second = await submitSample(app, 'foam-bank');
    await submitSample(app, 'foam-bank', { requestId: 'south-bank-foam-report', zoneId: 'south-bank' });
    await submitSample(app, 'algae');
    await submitSample(app, 'unclear');
    await submitSample(app, 'dumping', {
      observedAt: new Date(Date.now() - 49 * 3600000).toISOString(),
    });

    const [north, east, south] = await dashboard();
    assert.equal(north.status, 'priority_hotspot');
    assert.deepEqual(north.categories.map(item => [item.category, item.status, item.evidenceCount]), [
      ['foam', 'priority_hotspot', 2],
      ['algae_like_growth', 'watch', 1],
    ]);
    assert.deepEqual(north.categories[0].evidenceReportIds, [newer.id, second.id]);
    assert.ok(north.categories[0].reports[0].cue);
    assert.equal(east.status, 'none');
    assert.equal(south.status, 'watch');
    const history = await app.request('/api/reports').then(response => response.json());
    assert.equal(history.length, 7);
  } finally { app.close(); }
});
