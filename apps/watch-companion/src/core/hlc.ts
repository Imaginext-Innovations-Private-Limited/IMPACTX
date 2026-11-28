/**
 * Deterministic Hybrid Logical Clock (HLC) for the Tier-0 Watch node.
 *
 * Mirrors `packages/crdt-sync/src/aarogya_crdt_sync/hlc.py` with strict
 * monotonicity and total ordering on `(wall_ms, logical, node_id)`.
 */

import type { HlcTimestamp } from "../../../../packages/contracts/ts/index";

function assertValidWallMs(nowMs: number): number {
  if (!Number.isFinite(nowMs) || nowMs < 0) {
    throw new RangeError(`Physical timestamp must be a non-negative finite number, got ${nowMs}`);
  }
  return Math.trunc(nowMs);
}

/**
 * Create an HLC timestamp bound to `nodeId`.
 */
export function createHlc(
  nodeId: string,
  wallMs: number = 0,
  logical: number = 0,
): HlcTimestamp {
  if (!nodeId || nodeId.length > 128) {
    throw new RangeError("nodeId must be between 1 and 128 characters");
  }
  if (!Number.isInteger(logical) || logical < 0) {
    throw new RangeError(`logical counter must be a non-negative integer, got ${logical}`);
  }
  return {
    wall_ms: assertValidWallMs(wallMs),
    logical,
    node_id: nodeId,
  };
}

/**
 * Compare two HLC timestamps under total order `(wall_ms, logical, node_id)`.
 * Returns `-1` if `a < b`, `1` if `a > b`, or `0` if equal.
 */
export function compareHlc(a: HlcTimestamp, b: HlcTimestamp): -1 | 0 | 1 {
  if (a.wall_ms !== b.wall_ms) {
    return a.wall_ms < b.wall_ms ? -1 : 1;
  }
  if (a.logical !== b.logical) {
    return a.logical < b.logical ? -1 : 1;
  }
  if (a.node_id !== b.node_id) {
    return a.node_id < b.node_id ? -1 : 1;
  }
  return 0;
}

/**
 * Canonical `wall_ms:logical:node_id` representation matching `HlcTimestamp.to_sort_key()`.
 */
export function hlcSortKey(hlc: HlcTimestamp): string {
  return `${hlc.wall_ms}:${hlc.logical}:${hlc.node_id}`;
}

/**
 * Advance the local HLC for a local event, guaranteeing strict monotonicity.
 */
export function tickHlc(
  current: HlcTimestamp,
  nowMs: number = Date.now(),
): HlcTimestamp {
  const pt = assertValidWallMs(nowMs);
  if (pt > current.wall_ms) {
    return {
      wall_ms: pt,
      logical: 0,
      node_id: current.node_id,
    };
  }
  return {
    wall_ms: current.wall_ms,
    logical: current.logical + 1,
    node_id: current.node_id,
  };
}

/**
 * Merge a remote HLC timestamp on message/event receipt.
 * Guarantees the returned timestamp is strictly greater than both `current` and `remote`.
 */
export function receiveHlc(
  current: HlcTimestamp,
  remote: HlcTimestamp,
  nowMs: number = Date.now(),
): HlcTimestamp {
  const pt = assertValidWallMs(nowMs);
  const lOld = current.wall_ms;
  const lRemote = assertValidWallMs(remote.wall_ms);
  const lNew = Math.max(lOld, lRemote, pt);

  let logical: number;
  if (lNew === lOld && lNew === lRemote) {
    logical = Math.max(current.logical, remote.logical) + 1;
  } else if (lNew === lOld) {
    logical = current.logical + 1;
  } else if (lNew === lRemote) {
    logical = remote.logical + 1;
  } else {
    logical = 0;
  }

  return {
    wall_ms: lNew,
    logical,
    node_id: current.node_id,
  };
}
