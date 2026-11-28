const statuses = {
  open: 'Open', completed: 'Completed', cancelled: 'Cancelled', pending: 'Pending review',
  active: 'Active', declined: 'Declined', ended: 'Ended', assigned: 'Assigned',
  in_progress: 'In progress', awaiting_verification: 'Awaiting photo verification', verified: 'Verified',
};
const categories = {
  foam: 'Foam', algae_like_growth: 'Algae-like growth', dumping: 'Waste dumping',
  'suspected-discharge': 'Suspected discharge', sewage: 'Sewage or drain overflow', other: 'Shoreline concern',
};
const date = value => new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function button(label, run) {
  const control = element('button', label);
  control.className = 'secondary';
  control.type = 'button';
  control.addEventListener('click', () => run(control));
  return control;
}

function heading(parent, label) {
  const section = element('section');
  section.className = 'evidence-panel';
  section.append(element('h3', label));
  parent.append(section);
  return section;
}

function record(parent, label, ...details) {
  const item = element('article');
  item.className = 'pilot-record';
  item.append(element('h4', label), ...details.map(text => element('p', text)));
  parent.append(item);
  return item;
}

function field(name, label, options = {}) {
  const wrapper = element('label', label);
  const input = element(options.choices ? 'select' : options.long ? 'textarea' : 'input');
  input.name = name;
  input.required = true;
  if (options.choices) {
    input.append(new Option('Choose a photo report', ''));
    for (const [value, text] of options.choices) input.append(new Option(text, value));
  } else if (options.type) {
    input.type = options.type;
  } else {
    input.maxLength = options.long ? 500 : 120;
  }
  wrapper.append(input);
  return wrapper;
}

function form(parent, label, fields, submit, initial = {}) {
  const node = element('form');
  const control = element('button', label);
  control.type = 'submit';
  control.className = 'primary';
  node.append(...fields, control);
  node.addEventListener('submit', event => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(node));
    if (values.startsAt) values.startsAt = new Date(values.startsAt).toISOString();
    submit(control, { ...initial, ...values });
  });
  parent.append(node);
}

export function renderCommunityAlerts(panel, alerts, change) {
  const unread = alerts.filter(alert => !alert.read).length;
  const heading = element('h3', 'Lake alerts' + (unread ? ' · ' + unread + ' unread' : ''));
  const entries = element('ul');
  for (const alert of alerts) {
    const row = element('li', alert.lake + ' · ' + (categories[alert.category] ?? 'Shoreline concern') + ' · ' + date(alert.created_at));
    if (!alert.read) row.append(' ', button('Mark read', control => change(control, 'alert_read', { id: alert.id })));
    entries.append(row);
  }
  panel.replaceChildren(heading, alerts.length ? entries : element('p', 'No new alerts from your subscribed lakes.'));
}

export function renderCleanupManagement(panel, campaigns, change) {
  panel.replaceChildren();
  const action = (label, name, data) => button(label, control => change(control, name, data));
  const cleanup = heading(panel, 'Manage published cleanups');
  if (!campaigns.length) cleanup.append(element('p', 'No cleanups have been scheduled for this lake.'));
  form(cleanup, 'Publish authorised cleanup', [
    field('title', 'Campaign title'), field('details', 'Meeting point and safety instructions', { long: true }),
    field('startsAt', 'Start date and time (device time)', { type: 'datetime-local' }),
  ], (control, data) => change(control, 'campaign_create', data), { id: crypto.randomUUID() });
  for (const campaign of campaigns) {
    const row = record(cleanup, campaign.title, campaign.details,
      date(campaign.starts_at) + ' · ' + statuses[campaign.status] + ' · ' + campaign.registrations + ' registered');
    const id = campaign.id;
    if (campaign.status !== 'open') continue;
    const started = Date.parse(campaign.starts_at) <= Date.now();
    if (started) {
      for (const volunteer of campaign.roster ?? []) {
        const attendee = element('p', 'Check-in code ' + (volunteer.check_in_code ?? volunteer.id) + ' ');
        attendee.append(action(volunteer.attended ? 'Remove attendance' : 'Mark attended', 'attendance',
          { id, volunteerId: volunteer.id, attended: !volunteer.attended }));
        row.append(attendee);
      }
      row.append(action('Complete cleanup', 'campaign_finish', { id }));
    }
    row.append(action('Cancel cleanup', 'campaign_cancel', { id }));
  }
}

export function renderCommunityBoard(panel, board, { change, sector, showPhoto, prepareFollowUp }) {
  const { operator, adoptions, actions, reports, impact } = board;
  panel.replaceChildren();
  const reportChoices = candidates => candidates.map(row => [row.id, sector(row.zone_id) + ' · ' + date(row.observed_at)]);
  const action = (label, name, data) => button(label, control => change(control, name, data));
  const submit = name => (control, data) => change(control, name, data);
  if (!operator) {
    panel.append(action(board.subscribed ? 'Unsubscribe from lake alerts' : 'Subscribe to lake alerts',
      board.subscribed ? 'unsubscribe' : 'subscribe'));
  }

  const adoption = heading(panel, 'Lake adoption');
  if (!adoptions.length) adoption.append(element('p', 'No adoption records are available for this lake.'));
  if (!operator) form(adoption, 'Request lake adoption', [
    field('group', 'Community group name'), field('plan', 'Public stewardship plan', { long: true }),
  ], submit('adoption_request'), { id: crypto.randomUUID() });
  for (const entry of adoptions) {
    const row = record(adoption, entry.group_name, entry.plan, statuses[entry.status]);
    const id = entry.id;
    if (operator && entry.status === 'pending') {
      row.append(action('Approve adoption', 'adoption_approve', { id }), action('Decline adoption', 'adoption_decline', { id }));
    }
    if (operator && entry.status === 'active') row.append(action('End adoption', 'adoption_end', { id }));
  }

  const restoration = heading(panel, 'Restoration tracker');
  if (!actions.length) restoration.append(element('p', 'No corrective work has been assigned for this lake.'));
  if (operator && reports.length) form(restoration, 'Assign corrective work', [
    field('reportId', 'Verified pollution report', { choices: reportChoices(reports) }),
    field('assignee', 'Responsible team'), field('plan', 'Public corrective action summary', { long: true }),
  ], submit('restoration_create'), { id: crypto.randomUUID() });
  if (operator && !reports.length) restoration.append(element('p', 'Verify a pollution photo in Lake reports to assign corrective work.'));
  for (const entry of actions) {
    const row = record(restoration, sector(entry.zone_id) + ' · ' + statuses[entry.status],
      entry.assignee, entry.plan, ...(entry.progress ? [entry.progress] : []));
    const id = entry.id;
    if (operator && entry.status === 'assigned') row.append(action('Start corrective work', 'restoration_start', { id }));
    if (operator && entry.status === 'in_progress') form(row, 'Request photo verification',
      [field('progress', 'Work completed', { long: true })], submit('restoration_ready'), { id });
    if (entry.status !== 'awaiting_verification') continue;
    if (entry.evidence_pending) {
      row.append(element('p', 'Follow-up photo awaiting operator review.'));
      if (operator) {
        const reportId = entry.pending_evidence;
        const preview = element('div');
        const verify = action('Verify restoration', 'evidence_accept', { id, reportId });
        const reject = action('Reject follow-up photo', 'evidence_reject', { id, reportId });
        verify.disabled = reject.disabled = true;
        row.append(button('View follow-up photo', control => showPhoto(control, reportId, preview, () => {
          verify.disabled = reject.disabled = false;
        })), preview, verify, reject);
      }
    } else if (!operator) {
      const eligible = reports.filter(report => report.zone_id === entry.zone_id &&
        Date.parse(report.created_at) >= Date.parse(entry.ready_at) &&
        Date.parse(report.observed_at) >= Math.floor(Date.parse(entry.ready_at) / 60000) * 60000);
      row.append(element('p', 'Use a photo taken from a safe public location in this sector after ' + date(entry.ready_at) + '.'));
      if (eligible.length) form(row, 'Submit photo for verification', [
        field('reportId', 'Your follow-up photo', { choices: reportChoices(eligible) }),
      ], submit('evidence_submit'), { id });
      else {
        row.append(button('Upload a follow-up photo', () => prepareFollowUp(entry)));
      }
    }
  }

  const dashboard = heading(panel, 'Community impact');
  const metrics = element('dl');
  for (const [key, label] of Object.entries({
    completed_cleanups: 'Completed cleanups', volunteers: 'Volunteers who attended',
    active_adoptions: 'Active lake adoptions', verified_restorations: 'Verified restorations',
  })) metrics.append(element('dt', label), element('dd', String(impact[key])));
  dashboard.append(metrics);
}
