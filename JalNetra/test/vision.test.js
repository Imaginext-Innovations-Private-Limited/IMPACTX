import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createGeminiVision, createOpenAiVision, createReplayVision, getSample } from '../src/vision.js';
import { formFor, openApp } from '../test-support/http.js';
import { sampleForm } from '../test-support/samples.js';



test('offline vision identifies each labelled fixture and routes unmatched or unclear images to review', async () => {
  const app = openApp(':memory:', { vision: createReplayVision() });
  try {
    const status = await app.request('/api/status').then(response => response.json());
    assert.equal(status.mode, 'demo');
    assert.equal(status.samples.length, 6);
    const fixture = await app.request(status.samples[0].url);
    assert.equal(fixture.headers.get('content-type'), 'image/png');

    for (const [sample, outcome, category] of [
      ['foam-inlet', 'classified', 'foam'],
      ['algae', 'classified', 'algae_like_growth'],
      ['dumping', 'classified', 'dumping'],
      ['clear-view', 'no_target_signs'],
      ['unclear', 'needs_review'],
    ]) {
      const response = await app.request('/api/reports', { method: 'POST', body: sampleForm(sample) });
      assert.equal(response.status, 201);
      const report = await response.json();
      assert.equal(report.status, outcome);
      assert.equal(report.analysisSource, 'simulated');
      assert.equal(report.detections[0]?.category, category);
    }
    const body = formFor(new Date(Date.now() - 30000).toISOString());
    const unknown = await app.request('/api/reports', { method: 'POST', body }).then(response => response.json());
    assert.equal(unknown.status, 'needs_review');
    assert.match(unknown.reviewReason, /no demo result/);
  } finally { app.close(); }
});

test('invalid model output times out into or enters review and a retry reuses the report', async () => {
  let calls = 0;
  const vision = {
    source: 'simulated',
    analyse() {
      calls++;
      if (calls === 1) return new Promise(() => {});
      if (calls === 2) return { imageQuality: 'usable', detections: [{ category: 'unsupported', cue: 'mark' }] };
      return { imageQuality: 'usable', detections: [{ category: 'foam', cue: 'White froth' }] };
    },
  };
  const app = openApp(':memory:', { vision, timeoutMs: 30 });
  try {
    const result = await app.request('/api/reports', {
      method: 'POST', body: formFor(new Date(Date.now() - 30000).toISOString()),
    }).then(response => response.json());
    assert.equal(result.status, 'needs_review');
    assert.match(result.reviewReason, /timed out/);
    const retry = () => app.request('/api/reports/' + result.id + '/retry', { method: 'POST' }).then(response => response.json());
    const invalid = await retry();
    assert.equal(invalid.id, result.id);
    assert.match(invalid.reviewReason, /validated/);
    const classified = await retry();
    assert.equal(classified.id, result.id);
    assert.equal(classified.status, 'classified');
    assert.deepEqual(classified.detections, [{ category: 'foam', cue: 'White froth' }]);
    await retry();
    assert.equal(calls, 3);
  } finally { app.close(); }
});

test('live adapter sends image data and schema to Responses and validates the reply', async () => {
  let observed;
  const request = async (url, options) => {
    observed = { url, options };
    return Response.json({ status: 'completed', output: [{ content: [{
      type: 'output_text', text: JSON.stringify({ imageQuality: 'usable', detections: [] }),
    }] }] });
  };
  const adapter = createOpenAiVision({ apiKey: 'test-placeholder', model: 'test-vision', request });
  const result = await adapter.analyse({ png: getSample('foam-inlet').png });
  assert.equal(result.imageQuality, 'usable');
  assert.equal(observed.url, 'https://api.openai.com/v1/responses');
  const body = JSON.parse(observed.options.body);
  assert.equal(body.store, false);
  assert.equal(body.text.format.type, 'json_schema');
  assert.match(body.input[0].content[1].image_url, /^data:image\/png;base64,/);
});

test('Gemini sends the PNG and validates the structured shoreline assessment', async () => {
  const png = getSample('foam-inlet').png;
  const assessment = { imageQuality: 'usable', detections: [{ category: 'foam', cue: 'White froth' }] };
  const adapter = createGeminiVision({ apiKey: 'test-key', request: async (url, options) => {
    assert.equal(url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent');
    assert.equal(options.headers['x-goog-api-key'], 'test-key');
    const { contents, generationConfig } = JSON.parse(options.body);
    assert.deepEqual(contents[0].parts[1].inlineData, { mimeType: 'image/png', data: png.toString('base64') });
    assert.equal(generationConfig.responseMimeType, 'application/json');
    assert.deepEqual(generationConfig.responseJsonSchema.required, ['imageQuality', 'detections']);
    return Response.json({ candidates: [{ finishReason: 'STOP', content: { parts: [{ text: JSON.stringify(assessment) }] } }] });
  } });
  assert.deepEqual(await adapter.analyse({ png }), assessment);
});
