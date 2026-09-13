export interface CapturedFrame {
  id: number;
  blob: Blob;
  capturedAt: number;
}

const TRACE_PIPELINE = import.meta.env.VITE_TRACE_PIPELINE !== 'false';

class FrameService {
  private video: HTMLVideoElement | null = null;
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D | null = null;
  private intervalId: number | null = null;
  private targetFps: number = 12;
  private maxWidth = 640;
  private maxHeight = 480;
  private nextFrameId = 1;

  constructor() {
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
  }

  public setVideo(video: HTMLVideoElement): void {
    this.video = video;
  }

  public start(onFrame: (frame: CapturedFrame) => void): void {
    if (this.intervalId !== null) return;

    const captureInterval = 1000 / this.targetFps;
    
    this.intervalId = window.setInterval(() => {
      void this.captureFrame().then((frame) => { if (frame) onFrame(frame); });
    }, captureInterval);
  }

  public stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  public setTargetFps(fps: number): void {
    this.targetFps = fps;
    // We could restart the interval here to update immediately, but next stop/start is fine too
  }

  public async captureFrame(): Promise<CapturedFrame | null> {
    if (!this.video || !this.ctx || this.video.readyState !== this.video.HAVE_ENOUGH_DATA) {
      return null;
    }

    const id = this.nextFrameId++;
    const capturedAt = Date.now();
    if (TRACE_PIPELINE) console.log(`[PERCEPTA_TRACE] stage=1 frame=${id} ts=${capturedAt} captured`);

    // Match canvas to video size
    const scale = Math.min(1, this.maxWidth / this.video.videoWidth, this.maxHeight / this.video.videoHeight);
    const width = Math.max(1, Math.round(this.video.videoWidth * scale));
    const height = Math.max(1, Math.round(this.video.videoHeight * scale));
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }

    this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
    
    return new Promise((resolve) => this.canvas.toBlob((blob) => {
      if (!blob) {
        resolve(null);
        return;
      }
      const encodedAt = Date.now();
      if (TRACE_PIPELINE) console.log(`[PERCEPTA_TRACE] stage=2 frame=${id} ts=${encodedAt} encoded bytes=${blob.size}`);
      resolve({ id, blob, capturedAt });
    }, 'image/jpeg', 0.68));
  }
}

export const frameService = new FrameService();
