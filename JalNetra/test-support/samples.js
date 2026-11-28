import assert from 'node:assert/strict';
import { inflateSync } from 'node:zlib';
import { getSample } from '../src/vision.js';
import { formFor } from './http.js';

export function sampleForm(sampleId, { requestId = 'test-vision-' + sampleId, zoneId = 'north-inlet',
  observedAt = new Date(Date.now() - 30000).toISOString(), ...extra } = {}) {
  const png = getSample(sampleId).png;
  const photoWidth = png.readUInt32BE(16);
  const photoHeight = png.readUInt32BE(20);
  const stride = photoWidth * 3;
  const rows = inflateSync(png.subarray(41, 41 + png.readUInt32BE(33)));
  const pixels = Buffer.alloc(stride * photoHeight);
  for (let index = 0; index < photoHeight; index++) {
    assert.equal(rows[index * (stride + 1)], 0);
    const start = index * (stride + 1) + 1;
    rows.copy(pixels, index * stride, start, start + stride);
  }
  return formFor(observedAt, { requestId, zoneId, photoWidth, photoHeight, ...extra }, pixels);
}

export function submitSample(app, id, options) {
  return app.request('/api/reports', { method: 'POST', body: sampleForm(id, options) }).then(response => response.json());
}
