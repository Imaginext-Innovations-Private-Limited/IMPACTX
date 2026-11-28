import type { HlcTimestamp } from "./types";

export function compareHlc(a: HlcTimestamp, b: HlcTimestamp): number {
  return (
    a.wall_ms - b.wall_ms ||
    a.logical - b.logical ||
    (a.node_id < b.node_id ? -1 : a.node_id > b.node_id ? 1 : 0)
  );
}

/** Local event: mirrors HlcClock.tick in crdt-sync. */
export function tick(prev: HlcTimestamp, nowMs: number = Date.now()): HlcTimestamp {
  return nowMs > prev.wall_ms
    ? { wall_ms: nowMs, logical: 0, node_id: prev.node_id }
    : { wall_ms: prev.wall_ms, logical: prev.logical + 1, node_id: prev.node_id };
}

/** Remote merge: mirrors HlcClock.receive; result > both prev and remote. */
export function receive(
  prev: HlcTimestamp,
  remote: HlcTimestamp,
  nowMs: number = Date.now(),
): HlcTimestamp {
  const wall = Math.max(prev.wall_ms, remote.wall_ms, nowMs);
  let logical = 0;
  if (wall === prev.wall_ms && wall === remote.wall_ms) logical = Math.max(prev.logical, remote.logical) + 1;
  else if (wall === prev.wall_ms) logical = prev.logical + 1;
  else if (wall === remote.wall_ms) logical = remote.logical + 1;
  return { wall_ms: wall, logical, node_id: prev.node_id };
}
