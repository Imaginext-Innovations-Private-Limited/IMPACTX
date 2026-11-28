const windowDays = 30;
const limit = 100;

export function waterReadings(db, mode, lake, zoneId, now) {
  const current = new Date(now).toISOString();
  const from = new Date(now - windowDays * 86400000).toISOString();
  const items = db.prepare(`SELECT r.id, z.name AS zoneName, r.zone_id AS zoneId,
    r.observed_at AS observedAt, r.ph, r.temperature_c AS temperatureC,
    CASE WHEN r.request_id = 'rehearsal-first-report' THEN 'rehearsal' ELSE 'citizen' END AS readingSource
    FROM report r JOIN zone z ON r.zone_id = z.id
    WHERE r.data_mode = ? AND z.lake_name = ? AND (? IS NULL OR r.zone_id = ?)
      AND r.observed_at BETWEEN ? AND ? AND (r.ph IS NOT NULL OR r.temperature_c IS NOT NULL)
    ORDER BY r.observed_at DESC, r.id DESC LIMIT ?`)
    .all(mode, lake.name, zoneId, zoneId, from, current, limit);
  return { lakeId: lake.id, zoneId, windowDays, limit, items };
}
