import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createReplayVision } from '../src/vision.js';
import { createPilotComplaint } from '../src/complaints.js';
import { openApp, postJson } from '../test-support/http.js';
import { submitSample } from '../test-support/samples.js';

test('Devanahalli dumping draft gives the scoped municipal waste route', () => {
  const zone = { name: 'North sector' };
  const lake = { name: 'Devanahalli Lake', slug: 'devanahalli-lake' };
  const draft = createPilotComplaint(lake, zone, null, { category: 'dumping', evidence: [] });
  assert.equal(draft.recipient, 'Devanahalli Town Municipal Council');
  assert.match(draft.routingNote, /within town limits/);
  assert.equal(new URL(draft.routingSource.url).hostname, 'saiindia.gov.in');
  assert.equal(new URL(draft.filing.url).hostname, 'ipgrs.karnataka.gov.in');
  assert.match(draft.draftText, /coordinate with the lake custodian/);
  assert.equal(createPilotComplaint(lake, zone, null, { category: 'foam', evidence: [] }).routingNote, null);
});

test('complaints require a priority hotspot, preserve evidence, and export edits as text', async () => {
  const app = openApp(':memory:', { vision: createReplayVision() });
  const category = { zoneId: 'north-inlet', category: 'foam' };
  try {
    const one = await submitSample(app, 'foam-inlet', { ph: 7.2 });
    assert.equal((await postJson(app, '/api/complaints', category)).status, 409);
    const two = await submitSample(app, 'foam-bank');
    const result = await postJson(app, '/api/complaints', category);
    assert.equal(result.status, 201);
    const draft = await result.json();
    assert.deepEqual(new Set(draft.evidence.map(report => report.id)), new Set([one.id, two.id]));
    assert.match(draft.draftText, /DEMO DRAFT/);
    assert.match(draft.draftText, /Citizen-reported readings: pH 7\.2/);
    assert.match(draft.draftText, /North Inlet/);

    const route = '/api/complaints/' + draft.id;
    const edit = await app.request(route, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient: 'Demo ward office', draftText: 'Please inspect the inlet.' }),
    }).then(response => response.json());
    assert.equal(edit.recipient, 'Demo ward office');
    assert.deepEqual(edit.evidence, draft.evidence);
    const existing = await postJson(app, '/api/complaints', category);
    assert.equal(existing.status, 200);
    assert.equal((await existing.json()).id, draft.id);
    const exported = await app.request(route + '/export');
    assert.match(exported.headers.get('content-type'), /^text\/plain/);
    const text = await exported.text();
    assert.match(text, /To: Demo ward office/);
    assert.match(text, /Please inspect the inlet/);
    assert.ok(text.includes(one.id) && text.includes(two.id));
  } finally { app.close(); }
});
