export const pilotHotspotWindowMs = 48 * 60 * 60 * 1000;

export function latestPilotReview(report) {
  return (report.events ?? []).filter(event => event.action !== 'model').sort((a, b) =>
    b.created_at.localeCompare(a.created_at) || String(b.id).localeCompare(String(a.id)))[0];
}

export function groupPilotHotspots(reports, now) {
  const groups = new Map();
  for (const report of reports) {
    const age = now - Date.parse(report.observed_at);
    const review = latestPilotReview(report);
    if (!Number.isFinite(age) || age < 0 || age > pilotHotspotWindowMs ||
        !report.reporter_id || !review?.category || !['confirm', 'correct'].includes(review.action)) continue;
    const key = report.zone_id + ':' + review.category;
    if (!groups.has(key)) groups.set(key, { zoneId: report.zone_id, category: review.category, reports: new Map() });
    const reporters = groups.get(key).reports;
    const previous = reporters.get(report.reporter_id);
    if (!previous || report.observed_at > previous.observed_at ||
        (report.observed_at === previous.observed_at && report.id > previous.id)) reporters.set(report.reporter_id, report);
  }
  return [...groups.values()].map(group => {
    const evidence = [...group.reports.values()].sort((a, b) =>
      b.observed_at.localeCompare(a.observed_at) || b.id.localeCompare(a.id));
    return {
      zoneId: group.zoneId,
      category: group.category,
      status: evidence.length >= 2 ? 'priority_hotspot' : 'watch',
      evidence: evidence.map(report => ({
        id: report.id, observedAt: report.observed_at, ph: report.ph ?? null, temperatureC: report.temperature_c ?? null,
      })),
    };
  }).sort((a, b) => b.evidence.length - a.evidence.length || a.category.localeCompare(b.category));
}

