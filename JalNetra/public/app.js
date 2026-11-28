import { normalize } from './photo-input.js';
import { interactiveMap, nearestZone, placeMarkers, renderViewport, sectorAt } from './lake-map.js?v=shared-reporting';
import { readingText, renderReadings } from './readings.js';

const form = document.querySelector('#report-form');
const zone = document.querySelector('#zone');
const times = document.querySelector('#observed-at');
const photoInput = document.querySelector('#photo');
const preview = document.querySelector('#preview');
const status = document.querySelector('#form-status');
const submit = document.querySelector('#submit');
const markers = document.querySelector('#map-zones');
const historyStatus = document.querySelector('#history-status');
const reports = document.querySelector('#report-list');
const evidenceContent = document.querySelector('#evidence-content');
const hotspotLabels = { none: 'No active evidence', watch: 'Watch', priority_hotspot: 'Priority hotspot' };
let dashboard;
let zonesLoaded = false;
let lakes = [];
let currentLake;
let hostedReporting = true;
let hostedDemo = false;
let demoConcern;
const demoConcernStore = 'jalnetra-operator-demo';
const demoMarker = document.querySelector('#demo-alert-marker');
const demoLayer = document.querySelector('#demo-alert-layer');

function drawDemoAlert(viewport) {
  const target = lakes.find(item => item.id === 'devanahalli-lake');
  const selectedLake = currentLake?.kind === 'geographic';
  const visible = Boolean(demoConcern && target && (!selectedLake || currentLake.id === target.id));
  demoMarker.hidden = !visible;
  if (!visible) return;
  const point = selectedLake ? target.zones.find(zone => zone.name === demoConcern.sector) :
    { latitude: target.center[0], longitude: target.center[1] };
  if (point) placeMarkers([{ ...point, id: 'demo-alert' }], demoLayer, viewport);
}

function showDemoConcern(concern) {
  demoConcern = concern;
  const link = document.querySelector('#open-demo-operator');
  link.href = '/pilot.html?role=operator&lake=devanahalli-lake&demoRun=' + encodeURIComponent(concern.id);
  link.hidden = false;
  document.querySelector('#demo-concern-feedback').textContent =
    'Demo sent: ' + concern.title + ' � ' + concern.lake + ', ' + concern.sector + '.';
  cityController.redraw();
}

document.querySelector('#send-demo-concern').addEventListener('click', async event => {
  const button = event.currentTarget;
  const feedback = document.querySelector('#demo-concern-feedback');
  button.disabled = true;
  feedback.textContent = 'Sending a simulated concern to the operator.';
  try {
    const { concern } = await getJson('/api/pilot/demo-concern', jsonRequest('POST', {}));
    try { localStorage.setItem(demoConcernStore, JSON.stringify(concern)); } catch { /* The operator link still carries the run ID. */ }
    await setLake('devanahalli-lake');
    showDemoConcern(concern);
  } catch (error) {
    feedback.textContent = error.message || 'The demo concern could not be sent.';
  } finally {
    button.disabled = false;
  }
});
let readingRequest = 0;
const lakeSelect = document.querySelector('#lake-select');
const readingZone = document.querySelector('#reading-zone');
const gpsButton = document.querySelector('#gps-zone');
const gpsStatus = document.querySelector('#gps-status');
const map = document.querySelector('#lake-map');
const tiles = document.querySelector('#map-tiles');
const cityMap = document.querySelector('#city-map');
const cityGrid = document.querySelector('#city-grid');
const cityTiles = document.querySelector('#city-map-tiles');
const cityMarkers = document.querySelector('#city-markers');
const landmarkLayer = document.querySelector('#city-landmarks');
const lakeChoices = document.querySelector('#lake-choices');
const lakeSearch = document.querySelector('#lake-search');
const searchPanel = document.querySelector('#city-search-panel');
const lakeProfile = document.querySelector('#lake-profile');
const sectorChoices = document.querySelector('#sector-choices');
const concernBox = document.querySelector('#concern-box');
const concernForm = document.querySelector('#concern-form');
const concernZone = document.querySelector('#concern-zone');
const concernType = document.querySelector('#concern-type');
const concernStatus = document.querySelector('#concern-status');
const concernList = document.querySelector('#concern-list');
const concernSubmit = document.querySelector('#save-concern');
let concernRequest = crypto.randomUUID();
let concernLoad = 0;
const observationCard = document.querySelector('#observation-card');
const demoWorkspace = document.querySelector('#demo-workspace');
const demoGps = gpsButton.parentElement;
const demoGpsStatus = gpsStatus.parentElement;
const cityEvidence = document.querySelector('#city-evidence');
const evidencePanel = evidenceContent.parentElement;
const demoEvidence = evidencePanel.parentElement;
const landmarks = [
  { id: 'airport', label: 'Kempegowda Airport', latitude: 13.1986, longitude: 77.7066 },
  { id: 'electronic-city', label: 'Electronic City', latitude: 12.8479, longitude: 77.6633 },
];
const cityPoints = [];
let recentReportCount;
const draftDialog = document.querySelector('#draft-dialog');
const draftForm = document.querySelector('#draft-form');
const draftStatus = document.querySelector('#draft-status');
const recipientInput = document.querySelector('#recipient');
const draftText = document.querySelector('#draft-text');
const saveDraftButton = document.querySelector('#save-draft');
const downloadDraft = document.querySelector('#download-draft');
let currentDraft;
const rehearsalButton = document.querySelector('#restart-rehearsal');
let requestId = crypto.randomUUID();
let previewUrl;
let selectedFile;
let preparedPhoto;
let previewRevision = 0;
const sampleControl = document.querySelector('#sample-controls');
const sampleSelect = document.querySelector('#demo-sample');
const statusLabels = {
  pending: 'Pending analysis', needs_review: 'Needs review', classified: 'Signs detected',
  no_target_signs: 'No target signs detected',
};
const categoryLabels = { foam: 'Foam', algae_like_growth: 'Algae-like growth', dumping: 'Dumping' };
const sourceLabels = { simulated: 'Simulated', captured_replay: 'Demo replay', live_model: 'Live vision' };
const formatTime = new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata',
});

async function getJson(url, options) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error?.message || 'JalNetra could not complete the request.');
  return result;
}

function updateTimestamp() {
  const now = new Date();
  times.value = new Date(now - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function highlightZone() {
  if (concernZone.value !== zone.value) {
    concernZone.value = zone.value;
    concernRequest = crypto.randomUUID();
  }
  for (const marker of [...markers.children, ...sectorChoices.children]) {
    marker.setAttribute('aria-pressed', String(marker.dataset.zoneId === zone.value));
    const hotspot = dashboard?.zones.find(item => item.zoneId === marker.dataset.zoneId);
    marker.dataset.status = hotspot?.status ?? 'none';
    const status = marker.querySelector('.sector-status');
    if (status) {
      status.hidden = hostedReporting;
      status.textContent = dashboard ? hotspotLabels[marker.dataset.status] : 'Evidence status unavailable';
    }
    else marker.setAttribute('aria-label', hostedReporting ? marker.textContent : marker.textContent + ' - ' + hotspotLabels[marker.dataset.status]);
  }
  renderEvidence();
  const selected = currentLake?.zones.find(item => item.id === zone.value);
  document.querySelector('#selected-shoreline').hidden = !selected;
  document.querySelector('#selected-shoreline-label').textContent = selected ? currentLake.name + ' � ' + selected.name : '';
  updateLakeProfile();
}

function textElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
}

function appendReportContext(element, report) {
  const readings = readingText(report);
  if (readings) element.append(textElement('p', readings, 'reading-detail'));
  if (report.note) element.append(textElement('p', 'Note: ' + report.note));
}

function lakeEndpoint(path, zoneId) {
  const query = new URLSearchParams({ lakeId: currentLake.id });
  if (zoneId) query.set('zoneId', zoneId);
  return path + '?' + query;
}

function renderEvidence() {
  evidenceContent.replaceChildren();
  if (!dashboard) {
    evidenceContent.append(textElement('p', 'Loading zone evidence.'));
    return;
  }
  const selected = dashboard.zones.find(item => item.zoneId === zone.value) ??
    dashboard.zones.find(item => item.status === 'priority_hotspot') ??
    dashboard.zones.find(item => item.status === 'watch');
  if (!selected) {
    evidenceContent.append(textElement('p', 'No matching shoreline observations in the last 48 hours.'));
    return;
  }
  evidenceContent.append(textElement('p', selected.name + ' � ' + hotspotLabels[selected.status], 'evidence-zone'));
  if (!selected.categories.length) evidenceContent.append(textElement('p', 'No eligible reports in this zone.'));
  for (const group of selected.categories) {
    const card = document.createElement('article');
    card.className = 'evidence-group';
    const count = group.evidenceCount + (group.evidenceCount === 1 ? ' photo' : ' photos');
    card.append(textElement('h4', categoryLabels[group.category]),
      textElement('p', hotspotLabels[group.status] + ' � ' + count + ' in 48 hours'));
    const list = document.createElement('ul');
    for (const report of group.reports) {
      const row = document.createElement('li');
      const photo = document.createElement('img');
      photo.loading = 'lazy';
      photo.src = report.photoUrl;
      photo.alt = 'Evidence photo from ' + selected.name;
      const summary = document.createElement('div');
      summary.append(textElement('strong', report.cue),
        textElement('p', formatTime.format(new Date(report.observedAt)) + ' IST � ' + sourceLabels[report.analysisSource]),
        textElement('p', report.id));
      appendReportContext(summary, report);
      row.append(photo, summary);
      list.append(row);
    }
    card.append(list);
    if (group.status === 'priority_hotspot') {
      const button = textElement('button', 'Open complaint draft', 'secondary');
      button.type = 'button';
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          currentDraft = await getJson('/api/complaints', jsonRequest('POST', {
            zoneId: selected.zoneId, category: group.category,
          }));
          recipientInput.value = currentDraft.recipient ?? '';
          draftText.value = currentDraft.draftText;
          document.querySelector('#draft-evidence').textContent =
            'Evidence: ' + currentDraft.evidence.map(report => report.id).join(', ');
          draftStatus.textContent = '';
          draftDialog.showModal();
        } catch (error) {
          card.append(textElement('p', error.message, 'feedback error'));
        } finally {
          button.disabled = false;
        }
      });
      card.append(button);
    }
    evidenceContent.append(card);
  }
}

function jsonRequest(method, data) {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
}

async function saveDraft(download = false) {
  if (!currentDraft || !draftForm.reportValidity() || saveDraftButton.disabled) return;
  saveDraftButton.disabled = true;
  downloadDraft.disabled = true;
  draftStatus.textContent = '';
  draftStatus.className = 'feedback';
  try {
    const url = '/api/complaints/' + currentDraft.id;
    currentDraft = await getJson(url, jsonRequest('PATCH', {
      recipient: recipientInput.value, draftText: draftText.value,
    }));
    draftStatus.textContent = 'Draft saved.';
    if (download) {
      const link = document.createElement('a');
      link.href = url + '/export';
      link.download = currentDraft.id + '.txt';
      link.click();
    }
  } catch (error) {
    draftStatus.textContent = error.message;
    draftStatus.className = 'feedback error';
  } finally {
    saveDraftButton.disabled = false;
    downloadDraft.disabled = false;
  }
}

document.querySelector('#close-draft').addEventListener('click', () => draftDialog.close());
draftForm.addEventListener('submit', event => {
  event.preventDefault();
  saveDraft();
});
downloadDraft.addEventListener('click', () => saveDraft(true));

async function loadHotspots() {
  const lake = currentLake;
  try {
    const result = await getJson(lakeEndpoint('/api/hotspots'));
    if (lake !== currentLake) return;
    dashboard = result;
    highlightZone();
  } catch {
    if (lake !== currentLake) return;
    dashboard = undefined;
    evidenceContent.replaceChildren(textElement('p', 'Zone evidence could not be loaded. Refresh to try again.'));
  }
}

async function loadReadings() {
  const revision = ++readingRequest;
  const feedback = document.querySelector('#reading-status');
  feedback.textContent = 'Loading readings.';
  try {
    const view = await getJson(lakeEndpoint('/api/readings', readingZone.value));
    if (revision !== readingRequest) return;
    renderReadings(view.items, formatTime);
    feedback.textContent = view.items.length ? currentLake.name + ' � ' + view.items.length + ' recorded observations' :
      'No readings have been saved for this view.';
  } catch {
    if (revision !== readingRequest) return;
    renderReadings([], formatTime);
    feedback.textContent = 'Water readings could not be loaded. Refresh to try again.';
  }
}

function refreshDashboard() {
  if (hostedReporting) return Promise.resolve();
  return Promise.all([loadHistory(), loadHotspots(), loadReadings()]);
}

function setStatus(message, mood = '') {
  status.className = 'feedback ' + mood;
  status.textContent = message;
}

function clearPreview() {
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = undefined;
  selectedFile = undefined;
  preparedPhoto = undefined;
  preview.hidden = true;
  preview.removeAttribute('src');
}

function renderCity(viewport) {
  cityMap.dataset.zoom = viewport.zoom;
  if (currentLake?.kind === 'geographic') {
    renderViewport(cityTiles, currentLake.zones, markers, viewport);
    drawDemoAlert(viewport);
    return;
  }
  renderViewport(cityTiles, cityPoints, cityMarkers, viewport);
  placeMarkers(landmarks, landmarkLayer, viewport);
  drawDemoAlert(viewport);
  const labelBounds = [...landmarkLayer.children].filter(item => !item.hasAttribute('data-offscreen'))
    .map(item => item.getBoundingClientRect());
  for (const pin of cityMarkers.children) {
    const label = pin.firstElementChild;
    const box = label.getBoundingClientRect();
    const collision = labelBounds.some(other =>
      box.left < other.right + 4 && box.right > other.left - 4 &&
      box.top < other.bottom + 4 && box.bottom > other.top - 4);
    const suppress = pin.hasAttribute('data-offscreen') || collision;
    pin.toggleAttribute('data-small-label', suppress);
    if (!suppress) labelBounds.push(box);
  }
}

function selectShoreline(id) {
  if (zone.disabled) return;
  zone.value = id;
  gpsStatus.hidden = true;
  zone.dispatchEvent(new Event('change', { bubbles: true }));
}

function updateLakeProfile() {
  if (!currentLake) return;
  const real = currentLake.kind === 'geographic';
  for (const button of [...cityMarkers.children, ...lakeChoices.children]) {
    button.setAttribute('aria-pressed', String(button.dataset.mapId === currentLake.id));
  }
  lakeProfile.hidden = !real;
  cityGrid.classList.toggle('has-lake', real);
  searchPanel.hidden = real;
  cityMarkers.hidden = real;
  landmarkLayer.hidden = real;
  if (!real) return;
  document.querySelector('#profile-name').textContent = currentLake.name;
  document.querySelector('#profile-locality').textContent = currentLake.locality;
  document.querySelector('#profile-description').textContent = currentLake.description;
  const watch = dashboard?.zones.filter(item => item.status !== 'none').length;
  document.querySelector('#profile-observations').textContent =
    currentLake.zones.length + ' reporting sectors' +
    (recentReportCount === undefined ? '' : ' � ' + recentReportCount + ' recent observations') +
    (watch ? ' � ' + watch + ' sectors with active evidence' : '');
  document.querySelector('#lake-reference').href = currentLake.reference;
  const reportLink = document.querySelector('#profile-report');
  const target = new URL('/pilot.html?role=citizen', location.origin);
  target.searchParams.set('lake', currentLake.id);
  if (zone.value) target.searchParams.set('sector', zone.value);
  reportLink.href = target;
}

function filterLakeList() {
  const query = lakeSearch.value.trim().toLocaleLowerCase();
  let count = 0;
  for (const button of lakeChoices.children) {
    button.hidden = !button.dataset.search.includes(query);
    if (!button.hidden) count++;
  }
  document.querySelector('#lake-count').textContent = count ? count + ' mapped ' + (count === 1 ? 'lake' : 'lakes') : 'No matching lake';
}

function buildCityExplorer() {
  for (const landmark of landmarks) {
    const label = textElement('span', landmark.label, 'city-landmark');
    label.dataset.mapId = landmark.id;
    landmarkLayer.append(label);
  }
  for (const lake of lakes.filter(item => item.kind === 'geographic').sort((a, b) => a.name.localeCompare(b.name))) {
    const [latitude, longitude] = lake.center;
    cityPoints.push({ id: lake.id, latitude, longitude });
    const pin = document.createElement('button');
    pin.type = 'button';
    pin.className = 'city-pin';
    pin.dataset.mapId = lake.id;
    pin.setAttribute('aria-label', lake.name);
    pin.append(textElement('span', lake.name));
    const choice = textElement('button', lake.name, 'lake-choice');
    choice.type = 'button';
    choice.dataset.mapId = lake.id;
    choice.dataset.search = (lake.name + ' ' + lake.locality).toLocaleLowerCase();
    for (const button of [pin, choice]) {
      button.addEventListener('click', () => {
        if (lakeSelect.disabled) return;
        setLake(lake.id);
        lakeProfile.querySelector('#close-lake').focus({ preventScroll: true });
        cityGrid.scrollIntoView({ block: 'start' });
      });
    }
    cityMarkers.append(pin);
    lakeChoices.append(choice);
  }
  filterLakeList();
  cityController.redraw();
}

const cityController = interactiveMap(cityMap, renderCity, (viewport, x, y) => {
  if (currentLake?.kind !== 'geographic' || viewport.zoom < 13) return;
  const sector = sectorAt(currentLake, viewport, x, y);
  if (sector) selectShoreline(sector.id);
}, () => cityGrid.classList.contains('is-expanded'));

function resetCity() {
  if (lakeSelect.disabled) return;
  if (currentLake?.kind === 'geographic') {
    setLake('demo-lake');
    lakeSearch.focus({ preventScroll: true });
    document.querySelector('#city-title').scrollIntoView({ block: 'nearest' });
  } else {
    cityController.fit();
    cityMap.focus({ preventScroll: true });
  }
}

function setExpanded(expanded) {
  if (cityGrid.classList.contains('is-expanded') === expanded) return;
  cityGrid.classList.toggle('is-expanded', expanded);
  const button = document.querySelector('#map-expand');
  const label = expanded ? 'Minimize map' : 'Expand map';
  button.setAttribute('aria-expanded', String(expanded));
  button.textContent = label;
}

lakeSearch.addEventListener('input', filterLakeList);
lakeSearch.addEventListener('keydown', event => {
  if (event.key === 'Enter') lakeChoices.querySelector('button:not([hidden])')?.click();
});
document.querySelector('#map-zoom-in').addEventListener('click', () => cityController.zoomBy(1));
document.querySelector('#map-zoom-out').addEventListener('click', () => cityController.zoomBy(-1));
document.querySelector('#map-reset').addEventListener('click', resetCity);
document.querySelector('#close-lake').addEventListener('click', resetCity);
document.querySelector('#show-photo').addEventListener('click', () => {
  const field = zone.value ? photoInput : zone;
  field.focus({ preventScroll: true });
  field.scrollIntoView({ block: 'nearest' });
});
document.querySelector('#map-expand').addEventListener('click', () => setExpanded(!cityGrid.classList.contains('is-expanded')));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && cityGrid.classList.contains('is-expanded')) setExpanded(false);
});

function downloadConcern(concern, label) {
  const text = [
    'JalNetra citizen concern � Submitted by a member of the public', concern.id,
    concern.lakeName + ' � ' + concern.zoneName, label, 'Recorded ' + formatTime.format(new Date(concern.createdAt)) + ' IST',
    '', concern.description, '', 'This observation has not been independently verified.',
  ].join('\n');
  const link = document.createElement('a');
  link.href = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
  link.download = concern.id + '.txt';
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

async function loadConcerns() {
  const load = ++concernLoad;
  concernList.replaceChildren(textElement('li', 'Loading saved concerns.'));
  try {
    const items = await getJson(lakeEndpoint('/api/concerns'));
    if (load !== concernLoad) return;
    concernList.replaceChildren();
    for (const item of items) {
      const label = [...concernType.options].find(option => option.value === item.category).textContent;
      const entry = document.createElement('li');
      const button = textElement('button', 'Download concern', 'inline-action');
      button.type = 'button';
      button.addEventListener('click', () => downloadConcern(item, label));
      entry.append(textElement('strong', item.zoneName + ' � ' + label),
        textElement('p', item.description), textElement('p', item.id), button);
      concernList.append(entry);
    }
  } catch {
    if (load === concernLoad) concernList.replaceChildren(textElement('li', 'Saved concerns could not be loaded.'));
  }
}

concernBox.addEventListener('toggle', () => { if (concernBox.open) loadConcerns(); });
concernZone.addEventListener('change', () => selectShoreline(concernZone.value));
concernForm.addEventListener('input', () => { concernRequest = crypto.randomUUID(); });
concernForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (concernSubmit.disabled) return;
  const lake = currentLake;
  const id = concernRequest;
  const fields = Object.fromEntries(new FormData(concernForm));
  concernSubmit.disabled = true;
  concernStatus.textContent = 'Saving concern.';
  try {
    const concern = await getJson(lakeEndpoint('/api/concerns'),
      jsonRequest('POST', { ...fields, requestId: id }));
    if (currentLake !== lake) return;
    if (concernRequest === id) {
      concernForm.reset();
      concernZone.value = zone.value;
      concernRequest = crypto.randomUUID();
    }
    concernStatus.textContent = 'Concern saved. Reference ' + concern.id;
    await loadConcerns();
  } catch (error) {
    if (currentLake === lake) concernStatus.textContent = error.message;
  } finally {
    concernSubmit.disabled = false;
  }
});

function setLake(id) {
  const selected = lakes.find(item => item.id === id);
  if (!selected) return;
  const geographic = selected.kind === 'geographic';
  if (hostedDemo && geographic) return;
  if (currentLake === selected) {
    if (geographic) {
      cityController.fit(selected.zones, true);
    }
    return;
  }
  currentLake = selected;
  demoWorkspace.hidden = hostedReporting || geographic;
  cityEvidence.hidden = hostedReporting || !geographic;
  if (geographic) {
    cityMap.append(markers);
    document.querySelector('#city-report').append(observationCard);
    document.querySelector('#city-gps').append(gpsButton);
    document.querySelector('.profile-links').after(gpsStatus);
    cityEvidence.append(evidencePanel);
  } else {
    map.insertBefore(markers, document.querySelector('#map-attribution'));
    demoWorkspace.append(observationCard);
    demoGps.append(gpsButton);
    demoGpsStatus.insertBefore(gpsStatus, document.querySelector('#selected-shoreline'));
    demoEvidence.append(evidencePanel);
  }
  concernBox.open = false;
  concernForm.reset();
  concernStatus.textContent = '';
  concernList.replaceChildren();
  concernRequest = crypto.randomUUID();
  ++concernLoad;
  lakeProfile.parentElement.scrollTop = 0;
  lakeSelect.value = id;
  requestId = crypto.randomUUID();
  dashboard = undefined;
  recentReportCount = undefined;
  document.querySelector('#map-help').textContent = geographic
    ? 'Click a shoreline sector or its marker to set the location for your next upload.'
    : 'Select a marker to see the evidence for that zone or choose a zone in the form.';
  document.querySelector('#map-title').textContent = selected.name;
  document.querySelector('#map-kind').textContent = geographic ? 'Approximate zones' : 'Illustrative';
  document.querySelector('#illustrative-map').toggleAttribute('hidden', geographic);
  document.querySelector('#map-attribution').hidden = !geographic;
  tiles.hidden = !geographic;
  gpsButton.hidden = !geographic;
  gpsStatus.hidden = true;
  if (!geographic) tiles.replaceChildren();
  if (geographic && sampleSelect.value) {
    sampleSelect.value = '';
    photoInput.required = true;
    ++previewRevision;
    clearPreview();
  }
  sampleControl.hidden = geographic || samples.length === 0;
  zone.replaceChildren(new Option('Choose a zone', ''));
  concernZone.replaceChildren(new Option('Choose a side', ''));
  readingZone.replaceChildren(new Option('All zones', ''));
  markers.replaceChildren();
  sectorChoices.replaceChildren();
  for (const item of selected.zones) {
    zone.add(new Option(item.name, item.id));
    readingZone.add(new Option(item.name, item.id));
    const marker = document.createElement('button');
    marker.type = 'button';
    marker.className = 'marker';
    marker.textContent = item.name;
    marker.dataset.zoneId = item.id;
    marker.dataset.mapId = item.id;
    if (!geographic) {
      marker.style.left = item.markerX * 100 + '%';
      marker.style.top = item.markerY * 100 + '%';
    }
    marker.addEventListener('click', () => selectShoreline(item.id));
    markers.append(marker);
    if (geographic) {
      concernZone.add(new Option(item.name, item.id));
      const direction = document.createElement('button');
      direction.type = 'button';
      direction.className = 'sector-choice';
      direction.dataset.zoneId = item.id;
      direction.append(textElement('strong', item.name), textElement('span', '', 'sector-status'));
      direction.addEventListener('click', () => selectShoreline(item.id));
      sectorChoices.append(direction);
    }
  }
  const url = new URL(window.location.href);
  if (geographic) url.searchParams.set('lake', id);
  else url.searchParams.delete('lake');
  window.history.replaceState(null, '', url);
  const lakeParam = geographic ? '&lake=' + encodeURIComponent(id) : '';
  document.querySelector('#shared-reporting').href = '/pilot.html?role=citizen' + lakeParam;
  document.querySelector('#operator-reporting').href = '/pilot.html?role=operator' + lakeParam + '#pilot-operator';
  zonesLoaded = true;
  highlightZone();
  if (geographic) cityController.fit(selected.zones, true);
  else cityController.fit();
  renderReadings([], formatTime);
  return refreshDashboard();
}

async function loadLakes() {
  lakes = await getJson('/api/lakes');
  buildCityExplorer();
  for (const item of lakes) lakeSelect.add(new Option(item.name, item.id));
  const requested = hostedDemo ? 'demo-lake' : new URLSearchParams(window.location.search).get('lake');
  await setLake(lakes.some(item => item.id === requested) ? requested : 'demo-lake');
  if (hostedReporting) {
    try {
      const previous = JSON.parse(localStorage.getItem(demoConcernStore));
      if (previous?.id && Date.now() - Date.parse(previous.createdAt) < 86400000) showDemoConcern(previous);
    } catch { /* A fresh demo can still be sent. */ }
  }
}

lakeSelect.addEventListener('change', () => setLake(lakeSelect.value));
readingZone.addEventListener('change', loadReadings);
gpsButton.addEventListener('click', () => {
  const lake = currentLake;
  gpsStatus.hidden = false;
  if (!navigator.geolocation) {
    gpsStatus.textContent = 'GPS is unavailable in this browser. Choose a zone on the map or from the list.';
    return;
  }
  gpsButton.disabled = true;
  gpsStatus.textContent = 'Checking your location. Only the suggested zone is saved with your report.';
  navigator.geolocation.getCurrentPosition(({ coords }) => {
    gpsButton.disabled = false;
    if (lake !== currentLake) return;
    const suggested = nearestZone(lake, coords);
    if (!suggested) {
      gpsStatus.textContent = 'GPS is too far from this lake or too imprecise. Choose a zone manually.';
      return;
    }
    selectShoreline(suggested.id);
    gpsStatus.hidden = false;
    gpsStatus.textContent = 'Suggested zone is ' + suggested.name + '. Check the map and adjust if needed.';
  }, () => {
    gpsButton.disabled = false;
    if (lake === currentLake) gpsStatus.textContent = 'Location was unavailable. Choose a zone from the map or the list.';
  }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 });
});

async function loadHistory() {
  const lake = currentLake;
  try {
    const items = await getJson(lakeEndpoint('/api/reports'));
    if (lake !== currentLake) return;
    recentReportCount = items.length;
    updateLakeProfile();
    reports.replaceChildren();
    historyStatus.hidden = items.length > 0;
    historyStatus.textContent = 'Saved observations will appear here.';
    for (const item of items) {
      const row = document.createElement('li');
      const image = document.createElement('img');
      image.src = item.photoUrl;
      image.alt = 'Saved photo from ' + item.zoneName;
      image.loading = 'lazy';
      const detail = document.createElement('div');
      const title = document.createElement('strong');
      title.textContent = item.zoneName + ' � ' + formatTime.format(new Date(item.observedAt));
      const id = document.createElement('p');
      id.textContent = item.id;
      detail.append(title, id);
      appendReportContext(detail, item);
      for (const detection of item.detections) {
        const cue = document.createElement('p');
        cue.textContent = categoryLabels[detection.category] + ' - ' + detection.cue;
        detail.append(cue);
      }
      const notes = [sourceLabels[item.analysisSource], item.reviewReason].filter(Boolean);
      if (notes.length) {
        const reason = document.createElement('p');
        reason.textContent = notes.join(' � ');
        detail.append(reason);
      }
      if (item.canRetry) {
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'secondary';
        retry.textContent = 'Retry analysis';
        retry.addEventListener('click', async () => {
          retry.disabled = true;
          try {
            const updated = await getJson('/api/reports/' + item.id + '/retry', { method: 'POST' });
            setStatus(statusLabels[updated.status], updated.status === 'needs_review' ? 'error' : 'success');
            await refreshDashboard();
          } catch (error) {
            setStatus(error.message, 'error');
            retry.disabled = false;
          }
        });
        detail.append(retry);
      }
      const label = document.createElement('span');
      label.className = 'tag';
      label.textContent = statusLabels[item.status] ?? item.status;
      row.append(image, detail, label);
      reports.append(row);
    }
  } catch {
    if (lake !== currentLake) return;
    historyStatus.hidden = false;
    historyStatus.textContent = 'Recent observations could not be loaded. Refresh to try again.';
  }
}

form.addEventListener('input', () => { requestId = crypto.randomUUID(); });
form.addEventListener('change', () => { requestId = crypto.randomUUID(); });
zone.addEventListener('change', highlightZone);
function pickPhoto(file) {
  const revision = ++previewRevision;
  clearPreview();
  photoInput.setCustomValidity('');
  setStatus('');
  if (!file) return;
  selectedFile = file;
  requestId = crypto.randomUUID();
  preparedPhoto = normalize(file).then(result => {
    if (revision === previewRevision) {
      previewUrl = URL.createObjectURL(file);
      preview.src = previewUrl;
      preview.hidden = false;
    }
    return { result };
  }, error => {
    if (revision === previewRevision) {
      photoInput.setCustomValidity(error.message);
      setStatus(error.message, 'error');
    }
    return { error };
  });
}
photoInput.addEventListener('change', () => {
  sampleSelect.value = '';
  photoInput.required = true;
  pickPhoto(photoInput.files[0]);
});

let samples = [];
sampleSelect.addEventListener('change', async () => {
  const sample = samples.find(item => item.id === sampleSelect.value);
  if (!sample) return;
  const revision = ++previewRevision;
  clearPreview();
  photoInput.value = '';
  photoInput.setCustomValidity('');
  photoInput.required = true;
  setStatus('Loading sample.');
  try {
    const response = await fetch(sample.url);
    if (!response.ok) throw new Error('Sample could not be loaded.');
    const image = await response.blob();
    if (revision !== previewRevision) return;
    photoInput.required = false;
    pickPhoto(image);
  } catch (error) {
    if (revision === previewRevision) setStatus(error.message, 'error');
  }
});

async function loadMode() {
  const mode = await getJson('/api/status');
  document.querySelector('#app-mode').lastChild.textContent =
    mode.hosted ? ' Hosted demo' : mode.mode === 'live' ? ' Live vision' : mode.rehearsal ? ' Demo rehearsal' : ' Offline demo';
  if (mode.hosted) document.querySelector('#rehearsal-status').textContent =
    'Use the illustrated samples. Your browser has a separate demo session which expires after seven days.';
  hostedDemo = mode.hosted && new URLSearchParams(location.search).get('demo') === '1';
  hostedReporting = mode.hosted && !hostedDemo;
  document.querySelector('#app-mode').lastChild.textContent = hostedReporting ? ' Shared reporting' :
    hostedDemo ? ' Simulated demo' : document.querySelector('#app-mode').lastChild.textContent;
  if (hostedDemo) {
    document.querySelector('#title').textContent = 'Try the JalNetra demo';
    document.querySelector('#intro-description').textContent = 'Use sample photos to test how simulated observations become hotspots and complaint drafts.';
  }
  document.querySelector('#try-demo').hidden = !hostedReporting;
  document.querySelector('#demo-concern-tools').hidden = !hostedReporting;
  document.querySelector('#leave-demo').hidden = !hostedDemo;
  document.querySelector('#city-explorer').hidden = hostedDemo;
  document.querySelector('#profile-report').hidden = !hostedReporting;
  document.querySelector('#show-photo').hidden = hostedReporting;
  concernBox.hidden = hostedReporting;
  observationCard.hidden = hostedReporting;
  for (const id of ['readings-title', 'history-title']) {
    document.getElementById(id).closest('section').hidden = hostedReporting;
  }
  document.querySelector('#rehearsal-tools').hidden = !mode.rehearsal || hostedReporting;
  samples = mode.samples;
  sampleControl.hidden = samples.length === 0;
  for (const sample of samples) sampleSelect.add(new Option(sample.title, sample.id));
}

rehearsalButton.addEventListener('click', async () => {
  const feedback = document.querySelector('#rehearsal-status');
  if (!zonesLoaded) {
    feedback.textContent = 'Wait for the shoreline zones to load before starting the rehearsal.';
    return;
  }
  rehearsalButton.disabled = true;
  try {
    await getJson('/api/demo/reset', jsonRequest('POST', {}));
    currentDraft = undefined;
    if (draftDialog.open) draftDialog.close();
    rehearsalButton.textContent = 'Restart rehearsal';
    feedback.textContent = 'North Inlet is on Watch. Select “Foam from a second view” and save it at the same zone.';
    if (currentLake.id !== 'demo-lake') await setLake('demo-lake');
    zone.value = 'north-inlet';
    zone.dispatchEvent(new Event('change', { bubbles: true }));
    await refreshDashboard();
  } catch (error) {
    feedback.textContent = error.message;
  } finally {
    rehearsalButton.disabled = false;
  }
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (submit.disabled) return;
  if (!selectedFile) {
    setStatus('Choose a photo or a labelled demo sample.', 'error');
    return;
  }
  const payload = new FormData(form);
  const revision = previewRevision;
  const observedAt = new Date(times.value);
  if (!Number.isFinite(observedAt.valueOf())) {
    setStatus('Choose a valid observation time.', 'error');
    return;
  }
  payload.set('requestId', requestId);
  payload.set('observedAt', observedAt.toISOString());
  submit.disabled = true;
  submit.textContent = 'Saving…';
  setStatus('');
  const controls = [...form.elements, lakeSelect].filter(control => control !== submit && !control.disabled);
  for (const control of [...controls, ...markers.children]) control.disabled = true;
  try {
    const { result, error } = await preparedPhoto;
    if (error) throw error;
    payload.set('photo', result.pixels, 'photo.rgb');
    payload.set('photoWidth', String(result.width));
    payload.set('photoHeight', String(result.height));
    const report = await getJson('/api/reports', { method: 'POST', body: payload });
    if (revision === previewRevision) {
      form.reset();
      zone.value = report.zoneId;
      photoInput.required = true;
      ++previewRevision;
      clearPreview();
      highlightZone();
      updateTimestamp();
      requestId = crypto.randomUUID();
    }
    setStatus('Observation saved. ' + statusLabels[report.status] + '. Report ID ' + report.id, 'success');
    await refreshDashboard();
  } catch (error) {
    setStatus(error.message || 'The report could not be saved. Try again.', 'error');
  } finally {
    for (const control of [...controls, ...markers.children]) control.disabled = false;
    submit.disabled = false;
    submit.textContent = 'Save observation';
  }
});

updateTimestamp();
loadMode().then(loadLakes)
  .catch(() => setStatus('The demo could not be loaded. Refresh to try again.', 'error'));
