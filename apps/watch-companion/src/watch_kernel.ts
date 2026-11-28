/**
 * Autonomous Tier-0 Watch Kernel with dual-mode UX (CHW_COMPANION / PATIENT_FAMILY).
 *
 * Strictly typed against `packages/contracts/ts/index.ts` and backed by
 * `WatchStore` + HLC under `src/core/`.
 */

import {
  ActionCard,
  CONTRACT_SCHEMA_VERSION,
  CrdtEvent,
  HardwareCapabilityManifest,
  HlcTimestamp,
  SyncEnvelope,
  TriageAssessment,
  TriageSeverity,
  WatchMode,
} from "../../../packages/contracts/ts/index";
import {
  evaluateWatchDangerScreen,
  type WatchDangerScreenInput,
} from "./clinical/index";
import { WatchStore, type StorageLike } from "./core/index";

export interface WatchDangerCheckInput {
  patientId: string;
  unableToDrinkOrBreastfeed?: boolean;
  vomitsEverything?: boolean;
  convulsions?: boolean;
  lethargicOrUnconscious?: boolean;
  severeRespiratoryDistress?: boolean;
  severeBleeding?: boolean;
  vaginalBleeding?: boolean;
  severeHeadacheOrBlurredVision?: boolean;
  convulsionsOrFits?: boolean;
  dangerSigns?: readonly string[];
  language?: "en" | "hi" | "kn" | "ta";
}

export interface WatchScreenDangerOptions {
  persistActionCard?: boolean;
}

export interface WatchKernelOptions {
  storage?: StorageLike;
  storageKey?: string;
  store?: WatchStore;
  nowMs?: () => number;
}

export class WatchKernel {
  private readonly store: WatchStore;

  constructor(
    nodeId: string,
    initialMode: WatchMode = "CHW_COMPANION",
    options: WatchKernelOptions = {},
  ) {
    this.store =
      options.store ??
      new WatchStore({
        nodeId,
        initialMode,
        storage: options.storage,
        storageKey: options.storageKey,
        nowMs: options.nowMs,
      });
  }

  public getNodeId(): string {
    return this.store.getNodeId();
  }

  public getStore(): WatchStore {
    return this.store;
  }

  public getWatchMode(): WatchMode {
    return this.store.getWatchMode();
  }

  public setWatchMode(mode: WatchMode): WatchMode {
    return this.store.setWatchMode(mode);
  }

  public toggleWatchMode(): WatchMode {
    return this.store.toggleWatchMode();
  }

  public getManifest(batteryPct = 100): HardwareCapabilityManifest {
    return {
      node_id: this.store.getNodeId(),
      tier: "TIER_0_WATCH",
      ram_mb: 256,
      cpu_cores: 2,
      battery_pct: batteryPct,
      has_npu: false,
      installed_models: [],
      watch_mode: this.store.getWatchMode(),
    };
  }

  public tickHlc(): HlcTimestamp {
    return this.store.tickHlc();
  }

  /**
   * Deterministic Tier-0 danger-sign check: any single red flag forces RED_EMERGENCY.
   * Delegates to `evaluateWatchDangerScreen` and persists emitted CRDT events in `WatchStore`.
   */
  public screenDangerSigns(
    input: WatchDangerCheckInput | WatchDangerScreenInput,
    options: WatchScreenDangerOptions = {},
  ): {
    severity: TriageSeverity;
    event: CrdtEvent;
    assessment: TriageAssessment;
    actionCard: ActionCard | null;
    actionCardEvent: CrdtEvent | null;
  } {
    const result = evaluateWatchDangerScreen({
      ...input,
      nodeId: this.store.getNodeId(),
      tickHlc: () => this.tickHlc(),
      watchMode: this.store.getWatchMode(),
    });
    this.store.appendEvent(result.triageEvent, { enqueueOutbox: true });
    if (options.persistActionCard && result.actionCardEvent) {
      this.store.appendEvent(result.actionCardEvent, { enqueueOutbox: true });
    }
    return {
      severity: result.severity,
      event: result.triageEvent,
      assessment: result.assessment,
      actionCard: result.actionCard,
      actionCardEvent: result.actionCardEvent,
    };
  }

  public getVisibleActionCards(): ActionCard[] {
    return this.store.getVisibleActionCards();
  }

  public buildSyncEnvelope(
    sinceCursor: string | null = this.store.getSyncCursor(),
  ): SyncEnvelope {
    return {
      envelope_id: crypto.randomUUID(),
      sender_manifest: this.getManifest(),
      sender_hlc: this.tickHlc(),
      since_cursor: sinceCursor,
      next_cursor: null,
      events: this.store.getOutboxEvents(),
      ack_event_ids: [],
      schema_version: CONTRACT_SCHEMA_VERSION,
    };
  }

  public applySyncResponse(delta: SyncEnvelope): void {
    this.store.applySyncResponse(delta);
  }
}
