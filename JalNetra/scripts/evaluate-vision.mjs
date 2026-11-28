import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { createOpenAiVision, categories } from '../src/vision.js';

const manifest = process.argv[2];
if (!manifest) throw new Error('Usage: node scripts/evaluate-vision.mjs path/to/manifest.json');
const rows = JSON.parse(await readFile(manifest, 'utf8'));
if (!Array.isArray(rows) || !rows.length || rows.some(row =>
  typeof row?.file !== 'string' || !row.file.toLowerCase().endsWith('.png') ||
  !['usable', 'unclear'].includes(row.quality) || !Array.isArray(row.labels) ||
  row.labels.some(label => !categories.includes(label)) || (row.quality === 'unclear' && row.labels.length))) {
  throw new Error('Use a reviewed PNG manifest with file, quality (usable or unclear), and labels.');
}
const gateway = !process.env.OPENAI_API_KEY;
const model = process.env.JALNETRA_VISION_MODEL || (gateway ? 'openai/gpt-4.1-mini' : 'gpt-4.1-mini');
const vision = createOpenAiVision({ apiKey: process.env.OPENAI_API_KEY || process.env.AI_GATEWAY_API_KEY, model, gateway });
const metrics = Object.fromEntries(categories.map(label => [label, { tp: 0, fp: 0, fn: 0 }]));
const errors = [];
let reviewed = 0;
for (const row of rows) {
  const png = await readFile(resolve(dirname(manifest), row.file));
  if (png.length > 5 * 1024 * 1024 || png.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') {
    throw new Error('Use valid PNG files up to 5 MB: ' + row.file);
  }
  let result;
  try {
    result = await vision.analyse({ png, signal: AbortSignal.timeout(12000) });
  } catch (error) {
    errors.push({ file: row.file, issue: String(error.message).slice(0, 140) });
  }
  const predicted = result?.detections.map(item => item.category) ?? [];
  if (!result || result.imageQuality === 'unclear') reviewed++;
  if (result && (row.quality !== result.imageQuality ||
    row.labels.some(label => !predicted.includes(label)) || predicted.some(label => !row.labels.includes(label)))) {
    errors.push({ file: row.file, expected: row.labels, predicted, expectedQuality: row.quality, quality: result.imageQuality });
  }
  for (const label of categories) {
    const expected = row.labels.includes(label), actual = predicted.includes(label);
    if (expected && actual) metrics[label].tp++;
    if (!expected && actual) metrics[label].fp++;
    if (expected && !actual) metrics[label].fn++;
  }
}
for (const counts of Object.values(metrics)) {
  counts.precision = counts.tp + counts.fp ? counts.tp / (counts.tp + counts.fp) : null;
  counts.recall = counts.tp + counts.fn ? counts.tp / (counts.tp + counts.fn) : null;
}
console.log(JSON.stringify({ model, count: rows.length, reviewRate: reviewed / rows.length, metrics, errors }, null, 2));
