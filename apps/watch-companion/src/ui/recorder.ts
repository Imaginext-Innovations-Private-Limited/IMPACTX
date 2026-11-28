/**
 * Thin MediaRecorder wrapper for Tier-0 Watch SOS voice notes.
 * Gracefully reports unavailability when running without microphone permissions
 * or MediaRecorder support so the UI falls back to text SOS cleanly.
 */

export interface RecordedVoiceSos {
  blob: Blob;
  mimeType: string;
  durationMs: number;
}

export function isVoiceRecordingSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    typeof navigator.mediaDevices?.getUserMedia === "function" &&
    typeof MediaRecorder !== "undefined"
  );
}

export class WatchVoiceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: Blob[] = [];
  private startedAtMs = 0;

  public isRecording(): boolean {
    return this.mediaRecorder !== null && this.mediaRecorder.state === "recording";
  }

  public async start(): Promise<void> {
    if (!isVoiceRecordingSupported()) {
      throw new Error("Microphone recording is unavailable.");
    }
    if (this.isRecording()) {
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const preferredTypes = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg"];
    const mimeType =
      preferredTypes.find((type) =>
        typeof MediaRecorder.isTypeSupported === "function"
          ? MediaRecorder.isTypeSupported(type)
          : false,
      ) ?? "";

    const recorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream);

    this.stream = stream;
    this.mediaRecorder = recorder;
    this.chunks = [];
    this.startedAtMs = Date.now();

    recorder.addEventListener("dataavailable", (event: BlobEvent) => {
      if (event.data && event.data.size > 0) {
        this.chunks.push(event.data);
      }
    });

    recorder.start();
  }

  public async stop(): Promise<RecordedVoiceSos | null> {
    const recorder = this.mediaRecorder;
    if (!recorder) {
      return null;
    }

    return new Promise<RecordedVoiceSos | null>((resolve) => {
      const cleanup = () => {
        if (this.stream) {
          for (const track of this.stream.getTracks()) {
            track.stop();
          }
        }
        this.stream = null;
        this.mediaRecorder = null;
      };

      recorder.addEventListener(
        "stop",
        () => {
          const durationMs = Math.max(0, Date.now() - this.startedAtMs);
          const resolvedType = recorder.mimeType || "audio/webm";
          const blob = new Blob(this.chunks, { type: resolvedType });
          this.chunks = [];
          cleanup();
          resolve(blob.size > 0 ? { blob, mimeType: resolvedType, durationMs } : null);
        },
        { once: true },
      );

      if (recorder.state !== "inactive") {
        recorder.stop();
      } else {
        cleanup();
        resolve(null);
      }
    });
  }
}
