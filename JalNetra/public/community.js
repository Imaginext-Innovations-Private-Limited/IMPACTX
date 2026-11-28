
export function communityAdvice(signals = []) {
  const active = signals.filter(s => ['verified','pending'].includes(s.state));
  const categories = new Set(active.map(s => s.category));
  const advice = [];
  if (categories.has('foam') || categories.has('algae_like_growth')) advice.push('Avoid direct contact with affected water; keep children and pets away from visible foam or growth.');
  if (categories.has('dumping')) advice.push('Report waste from a safe shoreline. Join only authorised dry-land cleanups; do not handle hazardous waste.');
  if (categories.has('sewage') || categories.has('suspected-discharge')) advice.push('Stay away from suspected discharge points and request an operator inspection.');
  if (active.length && !advice.length) advice.push('Observe from a safe location and request an operator review.');
  if (!active.length) advice.push('No active concern in the available observations does not establish safe water. Check official advisories before contact.');
  return { active: active.length, verified: active.filter(s => s.state === 'verified').length, advice };
}
export function renderCommunity(panel, lake, signals, allSignals, allLakes) {
  const make = (tag, text) => { const n = document.createElement(tag); n.textContent = text; return n; };
  const read = () => { try { return JSON.parse(localStorage.getItem('jalnetra-community-v1')) || {}; } catch { return {}; } };
  const state = read();
  const save = () => { try { localStorage.setItem('jalnetra-community-v1', JSON.stringify(state)); return true; } catch { return false; } };
  const selected = state[lake.id] || {};
  const summary = communityAdvice(signals);
  panel.append(make('h3','Community protection and action'), make('p', 'Recent concern signals: '+summary.active+' · operator-verified signals: '+summary.verified+'. These are observations, not unique incidents or verified cleanup outcomes.'));
  const list = make('ul','');
  summary.advice.forEach(a => list.append(make('li',a)));
  panel.append(list);
  const follow = make('button', selected.follow ? 'Unfollow lake' : 'Follow lake');
  follow.type = 'button'; follow.className = 'secondary';
  const status = make('p','');
  status.setAttribute('role', 'status');
  const updates = make('ul','');
  const renderUpdates = () => {
    const followed = allLakes.filter(item => state[item.id]?.follow);
    const rows = followed.map(item => {
      const summary = communityAdvice(allSignals.filter(signal => signal.lake_id === item.id));
      return make('li', item.name + ' · ' + summary.active + ' recent concern signals');
    });
    if (!rows.length) rows.push(make('li', 'Follow a lake to see its current concern count here.'));
    updates.replaceChildren(...rows);
  };
  follow.onclick = () => {
    selected.follow = !selected.follow;
    state[lake.id] = selected;
    status.textContent = save() ? 'Lake preference saved on this device.' : 'Device storage unavailable.';
    follow.textContent = selected.follow ? 'Unfollow lake' : 'Follow lake';
    renderUpdates();
  };
  panel.append(follow,status,make('h4','Followed lake updates'));
  renderUpdates();
  panel.append(updates,make('h4','Personal lake stewardship plan'),make('p','Choose safe actions. This checklist is stored on this device only; it is not an event registration or proof of restoration.'));
  const tasks = ['Observe the shoreline from a safe public location','Share verified advisories with neighbours','Contact a recognised lake group about an authorised cleanup','Return for a follow-up observation after remediation'];
  tasks.forEach((task,i) => { const label = make('label',''); const input = document.createElement('input'); input.type='checkbox'; input.checked=Boolean(selected.tasks?.[i]); input.onchange=()=>{ selected.tasks ||= {}; selected.tasks[i]=input.checked; state[lake.id]=selected; status.textContent=save()?'Personal plan saved.':'Device storage unavailable.'; }; label.append(input,document.createTextNode(' '+task)); const row=make('p',''); row.append(label); panel.append(row); });
  panel.append(make('p','Do not enter contaminated water, collect unknown chemicals or attempt remediation without trained authorities.'));
}
