const readingLabel = source => source === 'rehearsal' ? 'Rehearsal sample' : 'Citizen-reported';

export function readingText(report) {
  const parts = [];
  if (Number.isFinite(report.ph)) parts.push('pH ' + report.ph);
  if (Number.isFinite(report.temperatureC)) parts.push(report.temperatureC + ' °C');
  return parts.length ? readingLabel(report.readingSource) + ' · ' + parts.join(' · ') : '';
}

const mediumDate = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: 'Asia/Kolkata' });

function plot(canvas, items, field, unit) {
  const points = items.filter(item => Number.isFinite(item[field]));
  canvas.hidden = points.length === 0;
  if (!points.length) return false;
  const ctx = canvas.getContext('2d');
  if (!ctx) return false;
  const width = canvas.width, height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const left = 57, right = width - 39, top = 19, bottom = height - 34;
  const times = points.map(item => Date.parse(item.observedAt));
  const first = Math.min(...times), last = Math.max(...times);
  const values = points.map(item => item[field]);
  const rawMin = Math.min(...values), rawMax = Math.max(...values);
  const minRange = field === 'ph' ? 1 : 4;
  const padding = Math.max(minRange / 2, (rawMax - rawMin) * .14);
  const low = rawMin - padding, high = rawMax + padding;
  const x = time => first === last ? (left + right) / 2 : left + (time - first) / (last - first) * (right - left);
  const y = value => bottom - (value - low) / (high - low) * (bottom - top);
  ctx.font = '14px system-ui';
  ctx.strokeStyle = '#d0dfd4';
  ctx.fillStyle = '#435f55';
  ctx.textAlign = 'right';
  for (let i = 0; i < 4; i++) {
    const value = low + (high - low) * i / 3;
    const row = y(value);
    ctx.beginPath();
    ctx.moveTo(left, row);
    ctx.lineTo(right, row);
    ctx.stroke();
    ctx.fillText(value.toFixed(1), left - 9, row + 5);
  }
  ctx.textAlign = first === last ? 'center' : 'left';
  ctx.fillText(mediumDate.format(first), x(first), height - 8);
  if (first !== last) {
    ctx.textAlign = 'right';
    ctx.fillText(mediumDate.format(last), x(last), height - 8);
  }
  ctx.fillStyle = field === 'ph' ? '#246e5a' : '#9a551c';
  for (const item of points) {
    ctx.beginPath();
    ctx.arc(x(Date.parse(item.observedAt)), y(item[field]), 5, 0, 2 * Math.PI);
    ctx.fill();
  }
  canvas.setAttribute('aria-label', points.length + ' ' + unit + ' readings over time. Exact readings are in the table below.');
  return true;
}

export function renderReadings(items, formatTime) {
  const body = document.querySelector('#reading-rows');
  const pH = plot(document.querySelector('#ph-chart'), items, 'ph', 'pH');
  const temperature = plot(document.querySelector('#temperature-chart'), items, 'temperatureC', 'temperature');
  document.querySelector('#ph-empty').hidden = pH;
  document.querySelector('#temperature-empty').hidden = temperature;
  document.querySelector('#readings-table').hidden = items.length === 0;
  body.replaceChildren();
  for (const item of items) {
    const tr = document.createElement('tr');
    for (const value of [
      formatTime.format(new Date(item.observedAt)), item.zoneName,
      item.ph ?? '—', item.temperatureC ?? '—', readingLabel(item.readingSource),
    ]) {
      const td = document.createElement('td');
      td.textContent = value;
      tr.append(td);
    }
    body.append(tr);
  }
}
