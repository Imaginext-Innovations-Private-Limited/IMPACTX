import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from 'playwright';
import { getSample } from '../src/vision.js';

const browser = await chromium.launch({
  executablePath: process.env.CHROME_BIN || (process.platform === 'win32'
    ? 'C:/Program Files/Google/Chrome/Application/chrome.exe' : '/usr/bin/google-chrome'),
});
const lake = { id: 'lake', name: 'Sample Lake', slug: 'sample-lake', pilot_zones: [{ id: 'zone', name: 'East sector' }] };
const report = { id: 'restoration-photo' };
const requests = [];
let submitted = false;
const page = await browser.newPage();
const errorMessages = [];
page.on('pageerror', error => errorMessages.push(error.message));
try {
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://localhost') return route.abort();
    const path = url.pathname;
    if (!path.startsWith('/api/')) {
      const file = path === '/' ? '/index.html' : path;
      try {
        const body = await readFile('public' + file);
        return route.fulfill({ body, contentType: file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html' });
      } catch { return route.fulfill({ status: 404, body: '' }); }
    }
    const endpoint = path.split('/').at(-1);
    if (route.request().method() === 'POST') {
      requests.push({ endpoint, body: endpoint === 'upload' ? route.request().postData() : route.request().postDataJSON() });
      if (endpoint === 'community') submitted = true;
    }
    const payloads = {
      signin: { access_token: 'organizer-session', refresh_token: 'organizer-refresh' },
      guest: { access_token: 'guest-session', refresh_token: 'guest-refresh' },
      account: { memberships: [{ lake_id: lake.id, role: 'citizen' }] },
      catalog: { lakes: [lake] },
      conditions: { signals: [] },
      reports: { reports: [] },
      concerns: { concerns: [] },
      drives: { drives: [{ id: 'cleanup', lake_id: lake.id, lake: lake.name, title: 'Sample cleanup',
        details: 'Meet at the gate', starts_at: '2099-01-01T04:00:00Z', joined: true, check_in_code: '8FBDA3CE21' }] },
      'drive-proposals': [{ id: 'previous', own: true, status: 'cancelled', title: 'Earlier cleanup',
        lake: lake.name, details: 'Meet at the gate', starts_at: '2026-01-01T04:00:00Z' }],
      community: { operator: false, campaigns: [], adoptions: [], reports: [], alerts: [], impact: {},
        actions: [{ id: 'work', zone_id: 'zone', status: 'awaiting_verification', assignee: 'Team',
          plan: 'Clear the path', ready_at: '2025-01-01T00:00:00Z', evidence_pending: submitted }] },
      upload: report,
    };
    return route.fulfill({ json: payloads[endpoint] ?? {} });
  });

  await page.goto('http://localhost/community.html');
  await page.getByText('Your volunteer check-in code: 8FBDA3CE21').waitFor();
  await page.getByLabel('Email', { exact: true }).fill('organizer@example.invalid');
  await page.getByLabel('Password', { exact: true }).fill('example-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByText('Cancelled', { exact: true }).waitFor();
  await page.locator('#drive-lake').selectOption(lake.id);
  await page.getByLabel('Organization or community group').fill('Lake volunteers');
  await page.getByLabel('Drive title').fill('Upcoming cleanup');
  await page.getByLabel('Start date and time (IST)').fill('2099-01-01T09:30');
  await page.getByLabel('Meeting point and safety instructions').fill('Meet at the gate.');
  await page.getByRole('button', { name: 'Submit for review' }).click();
  await page.getByText('Drive submitted for review.').waitFor();
  assert.equal(requests.find(entry => entry.endpoint === 'drive-proposals').body.startsAt, '2099-01-01T09:30:00+05:30');

  await page.goto('http://localhost/pilot.html?lake=sample-lake');
  await page.getByRole('button', { name: 'Upload a follow-up photo' }).click();
  await page.locator('#pilot-photo').setInputFiles({
    name: 'follow-up.png', mimeType: 'image/png',
    buffer: Buffer.from(getSample('dumping').png),
  });
  await page.getByRole('button', { name: 'Submit restoration photo' }).click();
  await page.getByText('Follow-up photo awaiting operator review.').waitFor();
  assert.match(requests.find(entry => entry.endpoint === 'upload').body, /name="purpose"\r\n\r\nrestoration/);
  assert.deepEqual(requests.find(entry => entry.endpoint === 'community').body,
    { action: 'evidence_submit', id: 'work', reportId: report.id });
  assert.ok(requests.every(entry => entry.endpoint !== 'preliminary'), 'follow-up skips preliminary analysis');
  assert.deepEqual(errorMessages, []);
  console.log('Passed community drive and restoration browser checks');
} finally {
  await browser.close();
}
