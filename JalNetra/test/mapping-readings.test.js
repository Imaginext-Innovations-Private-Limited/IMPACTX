import assert from 'node:assert/strict';
import { test } from 'node:test';
import { openApp, postJson } from '../test-support/http.js';
import { submitSample, sampleForm } from '../test-support/samples.js';
import { createReplayVision } from '../src/vision.js';
import { lakes } from '../src/lakes.js';
import { bengaluruExtent, fitMap, nearestZone, project, sectorAt, zoomViewport } from '../public/lake-map.js';
import { readingText } from '../public/readings.js';

test('GPS selects a nearby sector and rejects inaccurate or distant fixes', () => {
  const lake = lakes.find(item => item.id === 'ulsoor-lake');
  const north = lake.zones.find(item => item.id === 'ulsoor-north');
  assert.equal(nearestZone(lake, { ...north, accuracy: 14 }).id, north.id);
  assert.equal(nearestZone(lake, { ...north, accuracy: 151 }), null);
  assert.equal(nearestZone(lake, { latitude: 13.0085, longitude: 77.5741, accuracy: 9 }), null);
  assert.equal(nearestZone(lakes[0], { ...north, accuracy: 14 }), null);
  const projected = project(north.latitude, north.longitude, 16);
  const center = project(...lake.center, 16);
  assert.ok(projected.y < center.y);
  assert.ok(Math.abs(projected.x - center.x) < 0.01);
});

test('the city viewport fits named lakes and a projected shoreline point selects the expected sector', () => {
  const map = lakes.filter(lake => lake.center).map(lake => ({
    latitude: lake.center[0], longitude: lake.center[1],
  }));
  const city = fitMap(bengaluruExtent, 350, 300, 13, 32);
  for (const point of [...map, ...bengaluruExtent]) {
    const pos = project(point.latitude, point.longitude, city.zoom);
    assert.ok(pos.x - city.left >= 31 && pos.x - city.left <= 319);
    assert.ok(pos.y - city.top >= 31 && pos.y - city.top <= 269);
  }
  const lake = lakes.find(lake => lake.id === 'bellandur-lake');
  const shore = fitMap(lake.zones, 440, 300, 16, 46);
  const corner = lake.zones.find(zone => zone.id === 'bellandur-west');
  const click = project(corner.latitude, corner.longitude, shore.zoom);
  assert.equal(sectorAt(lake, shore, click.x - shore.left, click.y - shore.top).id, corner.id);
  const far = project(13.0085, 77.5741, shore.zoom);
  assert.equal(sectorAt(lake, shore, far.x - shore.left, far.y - shore.top), null);
});

test('wheel and pinch zoom keep the same map position under the pointer', () => {
  const city = fitMap(bengaluruExtent, 700, 420, 13, 32);
  const x = 254, y = 91;
  const zoomed = zoomViewport(city, city.zoom + 1, x, y);
  assert.equal((zoomed.left + x) / 2, city.left + x);
  assert.equal((zoomed.top + y) / 2, city.top + y);
  const pinch = zoomViewport(zoomed, city.zoom, x, y, x + 25, y + 15);
  assert.equal(pinch.left, city.left - 25);
  assert.equal(pinch.top, city.top - 15);
});

test('readings and hotspots stay scoped to lakes and zones, with demo reset isolation', async () => {
  const app = openApp(':memory:', { vision: createReplayVision(), rehearsal: true });
  const get = path => app.request(path).then(response => response.json());
  try {
    const mapped = await get('/api/lakes');
    assert.deepEqual(mapped.map(lake => lake.id), lakes.map(lake => lake.id));
    assert.ok(['devanahalli-lake', 'kengeri-lake', 'varthur-lake', 'veerasandra-lake']
      .every(id => mapped.some(lake => lake.id === id && lake.zones.length === 4)));
    assert.ok(mapped.filter(lake => lake.kind === 'geographic').every(lake => lake.locality && lake.reference));
    const bellandur = await submitSample(app, 'clear-view', {
      zoneId: 'bellandur-west', requestId: 'bellandur-corner-photo', ph: '',
    });
    assert.equal(bellandur.lakeName, 'Bellandur Lake');
    assert.equal(bellandur.zoneId, 'bellandur-west');
    assert.equal((await app.request(bellandur.photoUrl)).headers.get('content-type'), 'image/png');
    const electronicCity = await submitSample(app, 'clear-view', {
      zoneId: 'veerasandra-lake-east', requestId: 'electronic-city-photo', ph: 7.4, note: 'East side of Veerasandra',
    });
    assert.equal(electronicCity.lakeName, 'Veerasandra Lake');
    assert.equal((await get('/api/readings?lakeId=veerasandra-lake')).items[0].ph, 7.4);
    assert.deepEqual((await get('/api/zones?lakeId=sankey-tank')).map(zone => zone.lakeName),
      Array(4).fill('Sankey Tank'));

    const report = await submitSample(app, 'foam-inlet', {
      zoneId: 'ulsoor-north', ph: 7.2, temperatureC: 25.1, note: 'Taken next to the zone marker.',
    });
    await submitSample(app, 'foam-bank', { zoneId: 'ulsoor-east', ph: '', temperatureC: 24 });
    await submitSample(app, 'algae', {
      zoneId: 'ulsoor-east', ph: 6.8, observedAt: new Date(Date.now() - 31 * 86400000).toISOString(),
    });
    await submitSample(app, 'clear-view', { zoneId: 'sankey-south', ph: 0, temperatureC: '' });
    const readings = await get('/api/readings?lakeId=ulsoor-lake');
    assert.equal(readings.items.length, 2);
    assert.ok(readings.items.some(item => item.ph === null && item.temperatureC === 24));
    assert.equal((await get('/api/readings?lakeId=sankey-tank')).items[0].ph, 0);
    assert.equal((await get('/api/readings?lakeId=ulsoor-lake&zoneId=ulsoor-north')).items[0].id, report.id);
    assert.equal((await app.request('/api/readings?lakeId=ulsoor-lake&zoneId=sankey-north')).status, 400);
    assert.equal((await app.request('/api/readings?lakeId=unlisted')).status, 400);
    const hotspot = await get('/api/hotspots?lakeId=ulsoor-lake');
    const evidence = hotspot.zones[0].categories[0].reports[0];
    assert.equal(evidence.note, 'Taken next to the zone marker.');
    assert.equal(readingText(evidence), 'Citizen-reported · pH 7.2 · 25.1 °C');
    assert.ok((await get('/api/reports?lakeId=ulsoor-lake')).every(item => item.lakeName === 'Ulsoor Lake'));

    const invalid = await app.request('/api/reports', { method: 'POST',
      body: sampleForm('foam-inlet', { zoneId: 'ulsoor-north', ph: 14.1, requestId: 'test-invalid-ph' }),
    });
    assert.equal(invalid.status, 400);
    assert.equal((await postJson(app, '/api/demo/reset', {})).status, 200);
    assert.equal((await get('/api/readings?lakeId=demo-lake')).items[0].readingSource, 'rehearsal');
    assert.equal((await get('/api/readings?lakeId=ulsoor-lake')).items.length, 2);
  } finally {
    app.close();
  }
});
