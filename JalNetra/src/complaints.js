import { randomUUID } from 'node:crypto';
import { currentEvidence } from './hotspots.js';

export const categoryNames = {
  foam: 'visible foam', algae_like_growth: 'algae-like growth', dumping: 'visible dumped material',
};
const formatTime = new Intl.DateTimeFormat('en-IN', {
  dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Kolkata',
});

export function getDraft(db, mode, id) {
  const draft = db.prepare(`SELECT id, zone_id AS zoneId, category, recipient, draft_text AS draftText,
    created_at AS createdAt FROM complaint_draft WHERE data_mode = ? AND id = ?`).get(mode, id);
  if (!draft) return null;
  const evidence = db.prepare(`SELECT r.id, r.observed_at AS observedAt, e.attempt
    FROM complaint_evidence e JOIN report r ON r.id = e.report_id
    WHERE e.draft_id = ? ORDER BY r.observed_at DESC, r.id DESC`).all(id);
  return { ...draft, dataMode: mode, evidence };
}

function generatedText(mode, category, evidence) {
  const { lakeName, zoneName, latitude, longitude } = evidence[0];
  const subject = 'Request to inspect ' + categoryNames[category] + ' at ' + lakeName;
  const lines = [
    mode === 'demo' ? 'DEMO DRAFT — simulated observations. For demonstration only.' : 'DRAFT — verify the recipient and evidence before submitting.',
    '',
    'Subject: ' + subject,
    '',
    'Please inspect the shoreline at ' + zoneName + ', ' + lakeName + '.',
    evidence.length + ' distinct photos in the current 48-hour window show ' + categoryNames[category] + '.',
  ];
  if (latitude !== null && longitude !== null) lines.push('Approximate location: ' + latitude + ', ' + longitude);
  lines.push('', 'Supporting observations');
  for (const report of evidence) {
    lines.push('- ' + report.id + ' · ' + formatTime.format(new Date(report.observedAt)) + ' IST · ' + report.cue);
    lines.push('  Photo: ' + report.id + '.png');
    const readings = [];
    if (report.ph !== null) readings.push('pH ' + report.ph);
    if (report.temperatureC !== null) readings.push(report.temperatureC + ' °C');
    if (readings.length) lines.push((report.readingSource === 'rehearsal' ?
      '  Rehearsal sample readings: ' : '  Citizen-reported readings: ') + readings.join(', '));
  }
  lines.push('', 'Please review the observations and share any inspection findings.');
  return lines.join('\n');
}

export function createPilotComplaint(lake, zone, point, group) {
  const issue = categoryNames[group.category];
  const localContact = lake.slug === 'devanahalli-lake' ? {
    name: 'Devanahalli Town Municipal Council',
    url: 'https://bangalorerural.nic.in/en/public-utility/devanahalli-tmc/',
  } : null;
  const municipalDumping = localContact && group.category === 'dumping';
  const routingNote = municipalDumping
    ? 'Contact the council for municipal solid-waste inspection and cleanup within town limits. Confirm responsibility for the reported shoreline sector before filing.'
    : null;
  const routingSource = municipalDumping ? {
    name: 'Devanahalli solid-waste responsibility (CAG audit)',
    url: 'https://saiindia.gov.in/webroot/uploads/download_audit_report/2023/REPORT-3-ENGLISH-068a6cd1d278e17.59235279.pdf',
  } : null;
  const filing = { name: 'Karnataka Praja Seve grievance portal (iPGRS)', url: 'https://ipgrs.karnataka.gov.in/' };
  const lines = [
    'Subject: Request to inspect ' + issue + ' at ' + lake.name,
    '',
    'Please inspect the shoreline at ' + zone.name + ', ' + lake.name + '.',
    group.evidence.length + ' distinct citizens reported matching visible evidence within the last 48 hours. A lake operator reviewed the reports.',
  ];
  if (Number.isFinite(point?.latitude) && Number.isFinite(point?.longitude)) {
    lines.push('Approximate reporting sector: ' + point.latitude.toFixed(5) + ', ' + point.longitude.toFixed(5));
  }
  if (municipalDumping) lines.push('Please assess municipal solid-waste cleanup or coordinate with the lake custodian for the affected shoreline.');
  lines.push('', 'Supporting observations');
  for (const report of group.evidence) {
    lines.push('- ' + report.id + ' · ' + formatTime.format(new Date(report.observedAt)) + ' IST');
    const readings = [report.ph != null ? 'pH ' + report.ph : '',
      report.temperatureC != null ? report.temperatureC + ' °C' : ''].filter(Boolean);
    if (readings.length) lines.push('  Citizen-reported readings: ' + readings.join(', '));
  }
  lines.push('', 'Please share the inspection findings or forward this request to the responsible authority.');
  return { recipient: localContact?.name ?? '', localContact, filing, routingNote, routingSource,
    draftText: lines.join('\n'), evidence: group.evidence };
}

export function createDraft(db, mode, zoneId, category, now) {
  const evidence = currentEvidence(db, mode, now, zoneId, category);
  if (evidence.length < 2) return null;

  const latest = db.prepare(`SELECT id FROM complaint_draft WHERE data_mode = ? AND zone_id = ? AND category = ?
    ORDER BY created_at DESC, rowid DESC LIMIT 1`).get(mode, zoneId, category);
  const previous = latest && getDraft(db, mode, latest.id);
  if (previous && previous.evidence.length === evidence.length &&
      previous.evidence.every((item, index) => item.id === evidence[index].id && item.attempt === evidence[index].attempt)) {
    return { created: false, draft: previous };
  }

  const id = 'JD-' + randomUUID();
  db.prepare(`INSERT INTO complaint_draft (id, data_mode, zone_id, category, draft_text, created_at)
    VALUES (?, ?, ?, ?, ?, ?)`).run(id, mode, zoneId, category, generatedText(mode, category, evidence), new Date(now).toISOString());
  const insert = db.prepare(`INSERT INTO complaint_evidence (draft_id, data_mode, zone_id, category, report_id, attempt)
    VALUES (?, ?, ?, ?, ?, ?)`);
  for (const report of evidence) insert.run(id, mode, zoneId, category, report.id, report.attempt);
  return { created: true, draft: getDraft(db, mode, id) };
}

export function updateDraft(db, mode, id, recipient, draftText) {
  const result = db.prepare('UPDATE complaint_draft SET recipient = ?, draft_text = ? WHERE id = ? AND data_mode = ?')
    .run(recipient || null, draftText, id, mode);
  return result.changes ? getDraft(db, mode, id) : null;
}

export function exportDraft(draft) {
  return [
    draft.dataMode === 'demo' ? 'DEMO DRAFT — for demonstration only.' : 'DRAFT — review before submission.',
    'To: ' + (draft.recipient || '[Verify civic body]'),
    'Draft ID: ' + draft.id,
    '',
    draft.draftText,
    '',
    'Evidence record',
    ...draft.evidence.map(item => '- ' + item.id + ' · ' + item.observedAt),
    '',
  ].join('\n');
}
