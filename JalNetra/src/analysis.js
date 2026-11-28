import { validateVisionResult, VisionError } from './vision.js';

export function transact(db, work) {
  db.exec('BEGIN IMMEDIATE');
  try {
    const result = work();
    db.exec('COMMIT');
    return result;
  } catch (error) {
    db.exec('ROLLBACK');
    throw error;
  }
}

export function claimAttempt(db, report, vision, timeoutMs) {
  const current = db.prepare(`SELECT r.current_attempt AS attempt, p.png, a.status,
    a.expires_at AS expiresAt, r.image_fingerprint AS imageHash
    FROM report r JOIN report_photo p ON p.report_id = r.id
    LEFT JOIN analysis_attempt a ON a.report_id = r.id AND a.attempt = r.current_attempt
    WHERE r.id = ?`).get(report.id);
  if (!vision || !current || ['classified', 'no_target_signs'].includes(current.status)) return null;
  const now = new Date();
  if (current.status === 'pending' && Date.parse(current.expiresAt) > now.valueOf()) {
    return { busy: true };
  }
  if (current.status === 'pending') {
    db.prepare(`UPDATE analysis_attempt SET status = 'needs_review', finished_at = ?, review_reason = ?
      WHERE report_id = ? AND attempt = ?`).run(now.toISOString(), 'Previous analysis expired.', report.id, current.attempt);
  }
  const attempt = (current.attempt ?? 0) + 1;
  db.prepare(`INSERT INTO analysis_attempt (report_id, attempt, source, status, started_at, expires_at)
    VALUES (?, ?, ?, 'pending', ?, ?)`).run(
    report.id, attempt, vision.source, now.toISOString(), new Date(now.valueOf() + timeoutMs).toISOString(),
  );
  db.prepare('UPDATE report SET current_attempt = ? WHERE id = ?').run(attempt, report.id);
  return { id: report.id, attempt, png: current.png, imageHash: current.imageHash };
}

export async function runAttempt(db, attempt, vision, timeoutMs) {
  if (!attempt || attempt.busy) return;
  const controller = new AbortController();
  let timer;
  let result;
  let reason;
  try {
    const deadline = new Promise((_, reject) => {
      timer = setTimeout(() => {
        reject(new VisionError('Vision analysis timed out. Try again.'));
        controller.abort();
      }, timeoutMs);
    });
    const response = await Promise.race([
      deadline,
      vision.analyse({ png: attempt.png, imageHash: attempt.imageHash, signal: controller.signal }),
    ]);
    result = validateVisionResult(response);
    if (result.imageQuality === 'unclear') reason = 'The image is unclear. Try a clearer shoreline view.';
  } catch (error) {
    reason = error instanceof VisionError ? error.message : 'Vision analysis is unavailable. Try again.';
  } finally {
    clearTimeout(timer);
  }
  transact(db, () => {
    const status = reason ? 'needs_review' : result.detections.length ? 'classified' : 'no_target_signs';
    const update = db.prepare(`UPDATE analysis_attempt SET status = ?, image_quality = ?, review_reason = ?, finished_at = ?
      WHERE report_id = ? AND attempt = ? AND status = 'pending'
      AND attempt = (SELECT current_attempt FROM report WHERE id = ?)`).run(
      status, result?.imageQuality ?? null, reason ?? null, new Date().toISOString(),
      attempt.id, attempt.attempt, attempt.id,
    );
    if (!update.changes || reason) return;
    const save = db.prepare('INSERT INTO detection (report_id, attempt, category, cue) VALUES (?, ?, ?, ?)');
    for (const { category, cue } of result.detections) save.run(attempt.id, attempt.attempt, category, cue);
  });
}
