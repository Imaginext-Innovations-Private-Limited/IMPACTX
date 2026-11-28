import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createPilotHandler } from '../src/pilot.js';

const source = 'https://pilotexample.supabase.co';
const host = 'https://jalnetra.example';
const settings = { url: source, publishableKey: 'sb_publishable_example' };

test('community board accepts public reads and forwards only authenticated same-origin writes', async () => {
  const lakeId = 'c2000000-0000-4000-8000-000000000001';
  const route = host + '/api/jalnetra?jalroute=pilot/community&lakeId=' + lakeId;
  const authorization = 'Bearer demo.token.value';
  const calls = [];
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    calls.push([url.pathname, options.headers.Authorization, JSON.parse(options.body)]);
    return Response.json({});
  } });
  const write = (headers = {}) => new Request(route, {
    method: 'POST', headers, body: JSON.stringify({ action: 'subscribe' }),
  });
  assert.equal((await handle(new Request(route))).status, 200);
  assert.equal((await handle(new Request(route, { headers: { authorization } }))).status, 200);
  assert.equal((await handle(write({ origin: host }))).status, 401);
  assert.equal((await handle(write({ authorization, origin: source }))).status, 403);
  assert.equal((await handle(write({ authorization, origin: host }))).status, 200);
  assert.deepEqual(calls, [
    ['/rest/v1/rpc/pilot_community_board', undefined, { p_lake: lakeId }],
    ['/rest/v1/rpc/pilot_community_board', authorization, { p_lake: lakeId }],
    ['/rest/v1/rpc/pilot_community_change', authorization, { p_lake: lakeId, p_action: 'subscribe', p_data: {} }],
  ]);
});

test('pilot health verifies the Supabase schema over the Vercel rewrite', async () => {
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    assert.equal(url.href, source + '/rest/v1/rpc/jalnetra_pilot_status');
    assert.equal(options.headers.apikey, settings.publishableKey);
    assert.equal(options.headers.Authorization, undefined);
    return Response.json({ ready: true, schemaVersion: 1 });
  } });
  assert.equal(await handle(new Request(host + '/api/status')), null);
  const result = await handle(new Request(host + '/api/jalnetra?jalroute=pilot/status'));
  assert.deepEqual(await result.json(), { ready: true, provider: 'supabase', schemaVersion: 1 });
  assert.equal((await createPilotHandler()(new Request(host + '/api/pilot/status'))).status, 503);
});

test('pilot reports require a bearer token and forward it for row-level access', async () => {
  let calls = 0;
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    calls++;
    assert.equal(url.pathname, '/rest/v1/pilot_reports');
    assert.equal(url.searchParams.get('limit'), '25');
    assert.equal(options.headers.Authorization, 'Bearer demo.token.value');
    return calls === 1 ? Response.json([{ id: 'authorized-report' }]) : new Response(null, { status: 401 });
  } });
  const route = host + '/api/pilot/reports';
  assert.equal((await handle(new Request(route))).status, 401);
  assert.equal((await handle(new Request(route, { method: 'POST' }))).status, 405);
  assert.equal(calls, 0);
  const authorized = () => new Request(route, { headers: { Authorization: 'Bearer demo.token.value' } });
  assert.deepEqual(await (await handle(authorized())).json(), { reports: [{ id: 'authorized-report' }] });
  assert.equal((await handle(authorized())).status, 401);
});

test('pilot writes enforce same origin and allow only assigned operators to run live vision', async () => {
  const reportId = 'a1020000-0000-4000-8000-000000000001';
  const lakeId = 'a1020000-0000-4000-8000-000000000002';
  const user = 'a1020000-0000-4000-8000-000000000003';
  const report = { id: reportId, lake_id: lakeId, photo_path: user + '/' + reportId + '.png' };
  let operator = false, providerCalls = 0, saved, providerAvailable = false;
  const handle = createPilotHandler({ ...settings, apiKey: 'test', model: 'openai/test-model', gateway: true,
    async visionRequest(url, options) {
      assert.equal(url, 'https://ai-gateway.vercel.sh/v1/responses');
      assert.equal(JSON.parse(options.body).model, 'openai/test-model');
      providerCalls++;
      if (!providerAvailable) return new Response(null, { status: 503 });
      return Response.json({ status: 'completed', output: [{ content: [{ type: 'output_text',
        text: JSON.stringify({ imageQuality: 'usable', detections: [{ category: 'foam', cue: 'White bubbles along the shoreline' }] }),
      }] }] });
    },
    async request(url, options) {
      if (url.pathname === '/rest/v1/pilot_reports') return Response.json([report]);
      if (url.pathname === '/auth/v1/user') return Response.json({ id: user });
      if (url.pathname === '/rest/v1/pilot_memberships') {
        assert.equal(url.searchParams.get('user_id'), 'eq.' + user);
        return Response.json(operator ? [{ role: 'operator' }] : []);
      }
      if (url.pathname.startsWith('/storage/v1/object/authenticated/')) return new Response(Buffer.from([1, 2, 3]));
      if (url.pathname === '/rest/v1/pilot_review_events' && options.method === 'GET') return Response.json(saved ? [saved] : []);
      if (url.pathname === '/rest/v1/pilot_review_events' && options.method === 'POST') {
        saved = JSON.parse(options.body);
        return Response.json([saved], { status: 201 });
      }
      throw new Error('Unexpected request');
    },
  });
  const analyze = origin => handle(new Request(host + '/api/pilot/analyze', {
    method: 'POST', headers: { Authorization: 'Bearer demo.token.value', Origin: origin },
    body: JSON.stringify({ reportId }),
  }));
  assert.equal((await analyze('https://other.example')).status, 403);
  assert.equal((await analyze(host)).status, 403);
  assert.equal(providerCalls, 0);
  operator = true;
  const failed = await analyze(host);
  assert.equal(failed.status, 502);
  assert.equal((await failed.json()).error.code, 'VISION_UNAVAILABLE');
  assert.equal(saved, undefined);
  providerAvailable = true;
  assert.equal((await analyze(host)).status, 201);
  assert.equal(saved.model_output.detections[0].category, 'foam');
  assert.equal((await analyze(host)).status, 200);
  assert.equal(providerCalls, 2);
});

test('pilot enrollment accepts a successful empty response from Supabase', async () => {
  const userId = 'a1020000-0000-4000-8000-000000000003';
  const lakeId = 'a1020000-0000-4000-8000-000000000001';
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    if (url.pathname === '/auth/v1/user') return Response.json({ id: userId, email_confirmed_at: '2026-11-25' });
    assert.equal(url.pathname, '/rest/v1/pilot_memberships');
    assert.deepEqual(JSON.parse(options.body), { user_id: userId, lake_id: lakeId, role: 'citizen' });
    return new Response(null, { status: 201 });
  } });
  const response = await handle(new Request(host + '/api/pilot/enroll', {
    method: 'POST', headers: { Authorization: 'Bearer demo.token.value', Origin: host },
    body: JSON.stringify({ lakeId }),
  }));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { enrolled: true });
});


test('pilot hotspot map uses the latest eligible review and counts each citizen once', async () => {
  const lakeId = 'a1020000-0000-4000-8000-000000000002';
  const now = Date.now();
  const observed = age => new Date(now - age * 3600000).toISOString();
  const entry = (action, created_at, category = 'foam') => ({ action, created_at, category });
  const report = (id, reporter_id, zone_id, age, events) =>
    ({ id, reporter_id, zone_id, observed_at: observed(age), events, ph: 7.2 });
  const reviewed = [entry('confirm', observed(1))];
  const rows = [
    report('A', 'citizen-1', 'north', 2, reviewed),
    report('B', 'citizen-1', 'north', 3, reviewed),
    report('C', 'citizen-2', 'north', 4, reviewed),
    report('D', 'citizen-3', 'north', 2, [...reviewed, entry('dismiss', observed(0.5), null)]),
    report('E', 'citizen-4', 'north', 2, [...reviewed, entry('duplicate', observed(0.5), null)]),
    report('F', 'citizen-5', 'north', 49, reviewed),
    report('G', 'citizen-6', 'north', 1, [entry('model', observed(0))]),
    report('H', 'citizen-7', 'south', 1, reviewed),
    report('I', 'citizen-8', 'north', 2, [entry('correct', observed(1), 'dumping')]),
  ];
  let operator = false;
  const handle = createPilotHandler({ ...settings, async request(url) {
    if (url.pathname === '/auth/v1/user') return Response.json({ id: 'operator-1' });
    if (url.pathname === '/rest/v1/pilot_memberships') return Response.json(operator ? [{ role: 'operator' }] : []);
    assert.equal(url.pathname, '/rest/v1/pilot_reports');
    assert.equal(url.searchParams.get('lake_id'), 'eq.' + lakeId);
    assert.match(url.searchParams.get('and'), /^\(observed_at\.gte\..+,observed_at\.lte\./);
    return Response.json(rows);
  } });
  const dashboard = () => handle(new Request(host + '/api/pilot/hotspots?lakeId=' + lakeId, {
    headers: { Authorization: 'Bearer demo.token.value' },
  }));
  assert.equal((await dashboard()).status, 403);
  operator = true;
  const response = await dashboard();
  assert.equal(response.status, 200);
  const { groups } = await response.json();
  assert.deepEqual(groups.map(group => [group.zoneId, group.category, group.status,
    group.evidence.map(item => item.id)]), [
    ['north', 'foam', 'priority_hotspot', ['A', 'C']],
    ['north', 'dumping', 'watch', ['I']],
    ['south', 'foam', 'watch', ['H']],
  ]);
});


test('pilot complaint rechecks lake access and current Priority evidence before generating a draft', async () => {
  const lakeId = 'a1020000-0000-4000-8000-000000000002';
  const zoneId = 'a1020000-0000-4000-8000-000000000001';
  const recent = new Date(Date.now() - 60000).toISOString();
  const first = { id: 'report-one', zone_id: zoneId, reporter_id: 'citizen-1', observed_at: recent,
    ph: 7.2, events: [{ action: 'confirm', category: 'foam', created_at: recent }] };
  const second = { ...first, id: 'report-two', reporter_id: 'citizen-2', ph: null, temperature_c: 25 };
  let operator = false, reports = [first];
  const handle = createPilotHandler({ ...settings, async request(url) {
    if (url.pathname === '/auth/v1/user') return Response.json({ id: 'operator-1' });
    if (url.pathname === '/rest/v1/pilot_memberships') return Response.json(operator ? [{ role: 'operator' }] : []);
    if (url.pathname === '/rest/v1/pilot_reports') return Response.json(reports);
    assert.equal(url.pathname, '/rest/v1/pilot_lakes');
    return Response.json([{ name: 'Devanahalli Lake', slug: 'devanahalli-lake',
      pilot_zones: [{ id: zoneId, name: 'North sector', slug: 'devanahalli-lake-north' }] }]);
  } });
  const generate = () => handle(new Request(host + '/api/pilot/complaint', {
    method: 'POST', headers: { Authorization: 'Bearer demo.token.value', Origin: host },
    body: JSON.stringify({ lakeId, zoneId, category: 'foam' }),
  }));
  assert.equal((await generate()).status, 403);
  operator = true;
  assert.equal((await generate()).status, 409);
  reports = [first, second];
  const response = await generate();
  assert.equal(response.status, 200);
  const draft = await response.json();
  assert.equal(draft.recipient, 'Devanahalli Town Municipal Council');
  assert.match(draft.filing.url, /^https:\/\/ipgrs\.karnataka\.gov\.in\//);
  assert.match(draft.draftText, /North sector, Devanahalli Lake/);
  assert.match(draft.draftText, /Approximate reporting sector/);
  assert.match(draft.draftText, /report-one.+IST/);
  assert.match(draft.draftText, /report-two.+IST/);
  assert.match(draft.draftText, /Citizen-reported readings: pH 7\.2/);
  assert.match(draft.draftText, /Citizen-reported readings: 25 °C/);
  assert.equal(draft.evidence.length, 2);
  reports = [first, { ...second, events: [{ action: 'dismiss', created_at: recent }] }];
  assert.equal((await generate()).status, 409);
});

test('pilot photo intake validates readings and stores the normalized photo with its lake data', async () => {
  const citizenId = 'a1020000-0000-4000-8000-000000000001';
  const lakeId = 'a1020000-0000-4000-8000-000000000002';
  const zoneId = 'a1020000-0000-4000-8000-000000000003';
  const requestId = 'a1020000-0000-4000-8000-000000000004';
  let photo, saved;
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    if (url.pathname === '/auth/v1/user') return Response.json({ id: citizenId });
    if (url.pathname === '/rest/v1/pilot_memberships') return Response.json([{ role: 'citizen' }]);
    if (url.pathname === '/rest/v1/pilot_zones') return Response.json([{ id: zoneId }]);
    if (url.pathname === '/rest/v1/pilot_reports' && options.method === 'GET') return Response.json(saved ? [saved] : []);
    if (url.pathname.startsWith('/storage/v1/object/')) {
      photo = options.body;
      assert.equal(options.headers['Content-Type'], 'image/png');
      return new Response(null, { status: 201 });
    }
    assert.equal(url.pathname, '/rest/v1/pilot_reports');
    saved = { ...JSON.parse(options.body), id: 'stored-report' };
    return Response.json([saved], { status: 201 });
  } });
  const upload = ph => {
    const form = new FormData();
    for (const [key, value] of Object.entries({ id: requestId, lake_id: lakeId, zone_id: zoneId,
      observed_at: new Date().toISOString(), note: 'Shoreline observation', width: '2', height: '1',
      ph, temperature_c: '25.5',
    })) form.set(key, value);
    form.set('pixels', new Blob([Uint8Array.of(10, 20, 30, 40, 50, 60)]), 'photo.rgb');
    return handle(new Request(host + '/api/pilot/upload', {
      method: 'POST', headers: { Authorization: 'Bearer demo.token.value', Origin: host }, body: form,
    }));
  };
  assert.equal((await upload('17')).status, 400);
  assert.equal(photo, undefined);
  const response = await upload('7.2');
  assert.equal(response.status, 201);
  const report = await response.json();
  assert.equal(report.id, 'stored-report');
  assert.equal(report.zone_id, zoneId);
  assert.equal(report.ph, 7.2);
  assert.equal(report.temperature_c, 25.5);
  assert.equal(photo.subarray(1, 4).toString(), 'PNG');
});

test('pilot recovery requests return a generic response and password updates require auth', async () => {
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    if (url.pathname.endsWith('/recover')) {
      assert.equal(url.searchParams.get('redirect_to'), host + '/pilot.html');
      assert.equal(options.headers.Authorization, undefined);
      assert.deepEqual(JSON.parse(options.body), { email: 'citizen@example.invalid' });
      return Response.json({});
    }
    assert.equal(url.pathname, '/auth/v1/user');
    assert.equal(options.method, 'PUT');
    assert.equal(options.headers.Authorization, 'Bearer demo.token.value');
    assert.deepEqual(JSON.parse(options.body), { password: 'synthetic-long-password' });
    return Response.json({});
  } });
  const request = (route, body, token) => new Request(host + '/api/pilot/' + route, {
    method: 'POST', headers: { Origin: host, ...(token ? { Authorization: token } : {}) }, body: JSON.stringify(body),
  });
  const recovery = await handle(request('recover', { email: 'citizen@example.invalid' }));
  assert.equal(recovery.status, 200);
  assert.match((await recovery.json()).message, /If this address has an account/);
  assert.equal((await handle(request('recover', { email: 'invalid' }))).status, 400);
  const password = { password: 'synthetic-long-password' };
  assert.equal((await handle(request('password', password))).status, 401);
  assert.equal((await handle(request('password', password, 'Bearer demo.token.value'))).status, 200);
});

test('pilot paginates the review queue and checks lake operator access for pending reports', async () => {
  const lake = 'a1020000-0000-4000-8000-000000000002';
  let canReview = false;
  const handle = createPilotHandler({ ...settings, async request(url) {
    if (url.pathname === '/auth/v1/user') return Response.json({ id: 'operator' });
    if (url.pathname === '/rest/v1/pilot_memberships') {
      assert.equal(url.searchParams.get('lake_id'), 'eq.' + lake);
      return Response.json(canReview ? [{ role: 'operator' }] : []);
    }
    assert.equal(url.pathname, '/rest/v1/pilot_reports');
    assert.equal(url.searchParams.get('offset'), '25');
    assert.equal(url.searchParams.get('limit'), '26');
    assert.equal(url.searchParams.get('reviewed.action'), 'neq.model');
    assert.equal(url.searchParams.get('reviewed'), 'is.null');
    return Response.json(Array.from({ length: 26 }, (_, id) => ({ id })));
  } });
  const page = () => handle(new Request(host + '/api/pilot/reports?lakeId=' + lake + '&page=1&review=pending', {
    headers: { Authorization: 'Bearer demo.token.value' },
  }));
  assert.equal((await page()).status, 403);
  canReview = true;
  const result = await page();
  assert.equal(result.status, 200);
  const data = await result.json();
  assert.equal(data.reports.length, 25);
  assert.equal(data.hasMore, true);
});

test('citizen preliminary analysis saves verified provider output for their own photo', async () => {
  const reportId = 'a1020000-0000-4000-8000-000000000001';
  const person = 'a1020000-0000-4000-8000-000000000004';
  const report = { id: reportId, lake_id: reportId, photo_path: person + '/photo.png' };
  let actor = 'other-citizen', saved, visionCalls = 0;
  const output = { imageQuality: 'usable', detections: [{ category: 'dumping', cue: 'Bottles beside the water' }] };
  const handle = createPilotHandler({ ...settings, apiKey: 'test-key', model: 'test-model', analysisWriteToken: 'scoped-test-token',
    async visionRequest() {
      visionCalls++;
      return Response.json({ status: 'completed', output: [{ content: [{ type: 'output_text', text: JSON.stringify(output) }] }] });
    },
    async request(url, options) {
      if (url.pathname === '/auth/v1/user') return Response.json({ id: actor });
      if (url.pathname === '/rest/v1/pilot_reports') return Response.json([report]);
      if (url.pathname.startsWith('/storage/v1/object/authenticated/')) return new Response(Buffer.from([1, 2, 3]));
      if (url.pathname === '/rest/v1/pilot_review_events') return Response.json(saved ? [saved] : []);
      assert.equal(url.pathname, '/rest/v1/rpc/pilot_save_preliminary');
      assert.deepEqual(JSON.parse(options.body), { p_report: reportId, p_token: 'scoped-test-token', p_output: output });
      saved = { model_output: output };
      return Response.json(saved);
    },
  });
  const preliminary = () => handle(new Request(host + '/api/pilot/preliminary', {
    method: 'POST', headers: { Authorization: 'Bearer demo.token.value', Origin: host },
    body: JSON.stringify({ reportId }),
  }));
  assert.equal((await preliminary()).status, 403);
  assert.equal(visionCalls, 0);
  actor = person;
  assert.equal((await preliminary()).status, 201);
  assert.deepEqual(await (await preliminary()).json(), saved);
  assert.equal(visionCalls, 1);
});

test('citizen conditions are public and return aggregate lake signals', async () => {
  const signals = [{ lake_id: 'lake', zone_id: 'sector', state: 'verified', category: 'foam', observed_at: '2026-11-26T10:00:00Z' }];
  const handle = createPilotHandler({ ...settings, async request(url, options) {
    assert.equal(url.pathname, '/rest/v1/rpc/pilot_lake_conditions');
    assert.equal(options.headers.Authorization, undefined);
    return Response.json(signals);
  } });
  const response = await handle(new Request(host + '/api/pilot/conditions'));
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { signals });
});

test('pilot sign-in explains rejected credentials and unconfirmed email', async () => {
  const hostHeaders = { Origin: host, 'Content-Type': 'application/json' };
  const login = () => new Request(host + '/api/pilot/signin', {
    method: 'POST', headers: hostHeaders, body: JSON.stringify({ email: ' citizen@example.invalid ', password: 'a-test-password' }),
  });
  for (const [error_code, expected] of [
    ['invalid_credentials', 'INVALID_CREDENTIALS'], ['email_not_confirmed', 'EMAIL_NOT_CONFIRMED'],
  ]) {
    const handle = createPilotHandler({ ...settings, async request(url, options) {
      assert.equal(url.pathname, '/auth/v1/token');
      assert.equal(JSON.parse(options.body).email, 'citizen@example.invalid');
      return Response.json({ error_code }, { status: 400 });
    } });
    const response = await handle(login());
    assert.equal(response.status, 400);
    assert.equal((await response.json()).error.code, expected);
  }
});

test('a guest session returns auth tokens without exposing its stored credentials', async () => {
  const handle = createPilotHandler({ ...settings, guestWriteToken: 'server-only-token',
    async request(url, options) {
      if (url.pathname.endsWith('pilot_create_guest')) {
        const data = JSON.parse(options.body);
        assert.equal(data.p_token, 'server-only-token');
        assert.match(data.p_network, /^[a-f0-9]{64}$/);
        return Response.json({ email: 'guest@example.invalid', password: 'internal-only' });
      }
      assert.equal(url.pathname, '/auth/v1/token');
      assert.deepEqual(JSON.parse(options.body), { email: 'guest@example.invalid', password: 'internal-only' });
      return Response.json({ access_token: 'test.access.token', refresh_token: 'refresh', user: { email: 'guest@example.invalid' } });
    },
  });
  const response = await handle(new Request(host + '/api/pilot/guest', { method: 'POST', headers: { Origin: host }, body: '{}' }));
  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), { access_token: 'test.access.token', refresh_token: 'refresh' });
  assert.equal((await handle(new Request(host + '/api/pilot/account'))).status, 401);
});

test('public demonstration sends a scenario that an operator can verify without affecting real reports', async () => {
  const id = 'a1020000-0000-4000-8000-000000000042';
  let row;
  const handle = createPilotHandler({ ...settings, guestWriteToken: 'server-only-token',
    async request(url, options) {
      const body = JSON.parse(options.body);
      if (url.pathname.endsWith('/pilot_start_demo')) {
        assert.equal(options.headers.Authorization, undefined);
        assert.equal(body.p_token, 'server-only-token');
        assert.ok(['foam-inlet', 'algae', 'dumping'].includes(body.p_scenario));
        row = { id, scenario: body.p_scenario, created_at: '2026-11-26T10:00:00Z', confirmed_at: null };
        return Response.json(row);
      }
      assert.equal(url.pathname, '/rest/v1/rpc/pilot_demo_run');
      assert.equal(options.headers.Authorization, 'Bearer demo.token.value');
      assert.equal(body.p_id, id);
      if (body.p_confirm) row.confirmed_at = '2026-11-26T10:05:00Z';
      return Response.json(row);
    },
  });
  const start = await handle(new Request(host + '/api/pilot/demo-concern', { method: 'POST', headers: { Origin: host } }));
  assert.equal(start.status, 201);
  const { concern } = await start.json();
  assert.equal(concern.id, id);
  assert.match(concern.photoUrl, /^\/api\/demo\/samples\//);
  const url = host + '/api/pilot/demo-run';
  assert.equal((await handle(new Request(url + '?id=' + id))).status, 401);
  const operator = { Authorization: 'Bearer demo.token.value' };
  assert.deepEqual((await (await handle(new Request(url + '?id=' + id, { headers: operator }))).json()).concern, concern);
  const confirm = await handle(new Request(url, {
    method: 'POST', headers: { ...operator, Origin: host }, body: JSON.stringify({ id }),
  }));
  assert.equal((await confirm.json()).concern.confirmedAt, '2026-11-26T10:05:00Z');
});
