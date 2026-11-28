import { renderCleanupManagement } from './community-board.js';

const $ = id => document.getElementById(id);
const ist = { timeZone: 'Asia/Kolkata' };
const date = new Intl.DateTimeFormat('en-IN', { ...ist, dateStyle: 'full' });
const time = new Intl.DateTimeFormat('en-IN', { ...ist, timeStyle: 'short' });
function node(tag, text) {
  const element = document.createElement(tag);
  element.textContent = text;
  return element;
}

async function request(route, data, session) {
  const headers = {};
  if (session?.access_token) headers.Authorization = 'Bearer ' + session.access_token;
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const response = await fetch('/api/pilot/' + route, {
    method: data === undefined ? 'GET' : 'POST', headers, body: JSON.stringify(data),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(body.error?.message ?? 'The drive service is unavailable.'), { status: response.status });
  return body;
}

function driveCard(drive, showDetails) {
  const row = node('article', '');
  row.className = 'pilot-record';
  const start = new Date(drive.starts_at);
  const when = time.format(start) + ' IST';
  row.append(node('h3', drive.title), node('p', drive.lake + ' · ' + (showDetails ? date.format(start) + ' · ' : '') + when));
  if (drive.organization) row.append(node('p', 'Organized by ' + drive.organization));
  if (showDetails) row.append(node('p', drive.details));
  return row;
}

if ($('today-drives') && new URLSearchParams(location.search).get('demo') !== '1') {
  async function loadToday() {
    try {
      const { date: today, drives } = await request('drives?today=1');
      $('today-drives-date').textContent = drives.length ? date.format(new Date(today + 'T12:00:00+05:30')) : '';
      $('today-drives-list').replaceChildren(...drives.map(drive => driveCard(drive, false)));
      $('today-drives').hidden = !drives.length;
    } catch {
      $('today-drives').hidden = true;
    }
  }
  loadToday();
  setInterval(() => { if (!document.hidden) loadToday(); }, 60000);
}

if ($('drive-list')) {
  const operatorEntry = new URLSearchParams(location.search).get('role') === 'operator';
  const organizerKey = operatorEntry ? 'jalnetra-pilot-session' : 'jalnetra-community-session';
  const guestKey = 'jalnetra-guest-session';
  const authStatus = $('organizer-status');
  const driveStatus = $('drive-status');
  const refreshes = new Map();
  let proposalId = crypto.randomUUID();

  function read(store, key) {
    try { return JSON.parse(store.getItem(key)); } catch { return null; }
  }
  function save(store, key, value) {
    if (value) store.setItem(key, JSON.stringify({ access_token: value.access_token, refresh_token: value.refresh_token }));
    else store.removeItem(key);
  }
  async function api(route, data, guest = false) {
    const store = guest ? localStorage : sessionStorage;
    const key = guest ? guestKey : organizerKey;
    const session = read(store, key);
    try {
      return await request(route, data, session);
    } catch (error) {
      if (error.status !== 401 || !session?.refresh_token) throw error;
      if (!refreshes.has(key)) {
        refreshes.set(key, request('refresh', { refresh_token: session.refresh_token })
          .then(next => { save(store, key, next); return next; }).finally(() => refreshes.delete(key)));
      }
      return request(route, data, await refreshes.get(key));
    }
  }
  async function run(button, status, task) {
    if (button.disabled) return;
    button.disabled = true;
    status.textContent = '';
    try { await task(); } catch (error) { status.textContent = error.message; }
    finally { button.disabled = false; }
  }
  function action(label, status, task) {
    const button = node('button', label);
    button.type = 'button';
    button.className = 'secondary';
    button.addEventListener('click', () => run(button, status, task));
    return button;
  }
  let guestRequest;
  async function loadSchedule() {
    const { drives } = await api('drives', undefined, true);
    $('drive-list').replaceChildren(...drives.map(drive => {
      const row = driveCard(drive, true);
      if (drive.joined && drive.check_in_code) row.append(node('p', 'Your volunteer check-in code: ' + drive.check_in_code));
      if (Date.parse(drive.starts_at) <= Date.now()) {
        row.append(node('p', 'Registration closed'));
      } else {
        row.append(action(drive.joined ? 'Cancel registration' : 'Register as a volunteer', driveStatus, async () => {
          if (!read(localStorage, guestKey)) {
            guestRequest ??= request('guest', {}).then(session => save(localStorage, guestKey, session))
              .finally(() => { guestRequest = undefined; });
            await guestRequest;
          }
          await api('enroll', { lakeId: drive.lake_id }, true);
          await api('community?lakeId=' + encodeURIComponent(drive.lake_id), {
            action: drive.joined ? 'leave' : 'join', id: drive.id,
          }, true);
          await loadSchedule();
          driveStatus.textContent = drive.joined ? 'Registration cancelled.' : 'You are registered for this drive.';
        }));
      }
      return row;
    }));
    if (!drives.length) $('drive-list').append(node('p', 'No cleanup drives are scheduled.'));
  }
  async function loadProposals() {
    const proposals = await api('drive-proposals');
    $('drive-proposals').replaceChildren(...proposals.map(drive => {
      const row = driveCard(drive, true);
      row.append(node('p', { pending: 'Awaiting review', published: 'Published', declined: 'Declined',
        withdrawn: 'Withdrawn', completed: 'Completed', cancelled: 'Cancelled' }[drive.status]));
      const change = (label, command) => action(label, authStatus, async () => {
        await api('drive-proposals', { action: command, id: drive.id });
        await Promise.all([loadProposals(), loadSchedule(), loadManagement()]);
      });
      if (drive.own && drive.status === 'pending') row.append(change('Withdraw', 'withdraw'));
      if (drive.can_review) row.append(change('Approve and publish', 'publish'), change('Decline', 'decline'));
      return row;
    }));
    if (!proposals.length) $('drive-proposals').append(node('p', 'No submissions yet.'));
  }
  async function loadManagement() {
    const lake = $('drive-management-lake').value;
    const panel = $('drive-management-list');
    if (!lake) return panel.replaceChildren();
    const route = 'community?lakeId=' + encodeURIComponent(lake);
    const board = await api(route);
    if ($('drive-management-lake').value !== lake || $('drive-management').hidden) return;
    if (!board.operator) return panel.replaceChildren();
    renderCleanupManagement(panel, board.campaigns, (control, action, data) => run(control, authStatus, async () => {
      await api(route, { action, ...data });
      await Promise.all([loadSchedule(), loadManagement()]);
    }));
  }
  async function openWorkspace() {
    const signedIn = Boolean(read(sessionStorage, organizerKey));
    $('drive-auth').hidden = signedIn;
    $('drive-workspace').hidden = !signedIn;
    $('drive-signout').hidden = !signedIn;
    $('drive-management').hidden = true;
    if (signedIn) {
      const [{ lakes }, { memberships }] = await Promise.all([request('catalog'), api('account')]);
      $('drive-lake').replaceChildren(new Option('Choose a lake', ''), ...lakes.map(lake => new Option(lake.name, lake.id)));
      const assigned = new Set(memberships.filter(item => ['admin', 'operator'].includes(item.role)).map(item => item.lake_id));
      $('drive-management-lake').replaceChildren(...lakes.filter(lake => assigned.has(lake.id))
        .map(lake => new Option(lake.name, lake.id)));
      $('drive-management').hidden = !assigned.size;
      await Promise.all([loadProposals(), loadManagement()]);
    } else $('drive-proposals').replaceChildren();
  }

  $('drive-refresh').addEventListener('click', event => run(event.currentTarget, driveStatus, loadSchedule));
  $('drive-management-lake').addEventListener('change', () => loadManagement().catch(error => {
    authStatus.textContent = error.message;
  }));
  $('drive-auth').addEventListener('submit', event => {
    event.preventDefault();
    const button = event.submitter;
    run(button, authStatus, async () => {
      const data = Object.fromEntries(new FormData(event.target));
      const result = await request(button.value, data);
      $('community-password').value = '';
      if (button.value === 'signup') {
        authStatus.textContent = 'Confirm your email using the link we sent, then return here to sign in.';
        return;
      }
      save(sessionStorage, organizerKey, result);
      await openWorkspace();
    });
  });
  $('drive-signout').addEventListener('click', event => run(event.currentTarget, authStatus, async () => {
    try { await api('signout', {}); } finally {
      save(sessionStorage, organizerKey, null);
      $('drive-form').reset();
      await openWorkspace();
    }
  }));
  $('drive-form').addEventListener('input', () => { proposalId = crypto.randomUUID(); });
  $('drive-form').addEventListener('submit', event => {
    event.preventDefault();
    run(event.submitter, authStatus, async () => {
      const data = Object.fromEntries(new FormData(event.target));
      await api('drive-proposals', { ...data, action: 'submit', id: proposalId, startsAt: data.startsAt + ':00+05:30' });
      event.target.reset();
      proposalId = crypto.randomUUID();
      await loadProposals();
      authStatus.textContent = 'Drive submitted for review.';
    });
  });
  loadSchedule().catch(error => { driveStatus.textContent = error.message; });
  openWorkspace().catch(error => { authStatus.textContent = error.message; });
}
