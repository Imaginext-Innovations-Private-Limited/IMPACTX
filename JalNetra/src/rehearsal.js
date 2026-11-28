import { claimAttempt, runAttempt, transact } from './analysis.js';
import { getSample } from './vision.js';

export async function resetRehearsal(db, vision, timeoutMs, saveReport) {
  const sample = getSample('foam-inlet');
  const attempt = transact(db, () => {
    // The caller provides an isolated local rehearsal or hosted demo session.
    const demoZone = "SELECT id FROM zone WHERE lake_name = 'Demo Lake'";
    const demoReport = `SELECT id FROM report WHERE zone_id IN (${demoZone})`;
    const demoDraft = `SELECT id FROM complaint_draft WHERE zone_id IN (${demoZone})`;
    db.exec(`DELETE FROM complaint_evidence WHERE draft_id IN (${demoDraft});
      DELETE FROM complaint_draft WHERE zone_id IN (${demoZone});
      UPDATE report SET current_attempt = NULL WHERE id IN (${demoReport});
      DELETE FROM detection WHERE report_id IN (${demoReport});
      DELETE FROM analysis_attempt WHERE report_id IN (${demoReport});
      DELETE FROM report WHERE id IN (${demoReport});`);
    const observedAt = new Date(Date.now() - 60 * 1000).toISOString();
    const result = saveReport(db, {
      requestId: 'rehearsal-first-report', fingerprint: sample.imageHash, hash: sample.imageHash,
      png: sample.png, zoneId: 'north-inlet', observedAt, note: '', ph: 7.1, temperature: 24.6,
    }, 'demo');
    return claimAttempt(db, result, vision, timeoutMs);
  });
  await runAttempt(db, attempt, vision, timeoutMs);
  return attempt.id;
}
