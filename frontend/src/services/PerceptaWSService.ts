import { PerceptionResult } from '../types/perception';
import { ConnectionStatus } from '../types/events';
import { PercetpaSettings } from '../types/settings';
import { CapturedFrame } from './FrameService';

const TRACE_PIPELINE = import.meta.env.VITE_TRACE_PIPELINE !== 'false';

class PerceptaWSService {
  private ws: WebSocket | null = null;
  private onPerceptionCallback: ((result: PerceptionResult) => void) | null = null;
  private onStatusCallback: ((status: ConnectionStatus) => void) | null = null;
  private onMessageCallback: ((message: string | null) => void) | null = null;
  private reconnectInterval = 1000;
  private maxReconnectInterval = 30000;
  private url: string = '';
  private intentionallyDisconnected = false;
  private reconnectTimer: number | null = null;
  private frameInFlight = false;
  private pendingModalities = { face: true, hand: true, voice: true };

  public connect(url: string): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.url = url;
    this.intentionallyDisconnected = false;
    this.updateStatus('connecting');

    try {
      const socket = new WebSocket(url);
      this.ws = socket;
      
      socket.onopen = () => {
        if (this.ws !== socket) return;
        this.updateStatus('connected');
        this.updateMessage('Preparing the local perception pipeline…');
        this.sendPendingModalities();
        this.reconnectInterval = 1000; // Reset backoff
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'status' && data.state === 'initializing') {
            this.updateStatus('initializing');
            return;
          }
          if (data.type === 'error') {
            console.error(data.message);
            this.updateStatus('error');
            this.updateMessage(data.message || 'The perception backend returned an error.');
            this.frameInFlight = false;
            return;
          }
          if (data.type === 'perception' && this.onPerceptionCallback) {
            const receivedAt = Date.now();
            if (TRACE_PIPELINE && data.trace_frame_id !== undefined) console.log(`[PERCEPTA_TRACE] stage=7 frame=${data.trace_frame_id} ts=${receivedAt} event_received`);
            this.frameInFlight = false;
            this.updateMessage(null);
            this.onPerceptionCallback(data as PerceptionResult);
          } else if (data.type === 'status') {
            this.updateMessage(data.message || null);
          } else if (data.type === 'error') {
            this.frameInFlight = false;
            this.updateStatus('error');
            this.updateMessage(data.message || 'The perception backend returned an error.');
          }
        } catch (e) {
          console.error('Failed to parse WS message', e);
        }
      };

      socket.onclose = () => {
        if (this.ws !== socket) return;
        this.ws = null;
        this.frameInFlight = false;
        if (!this.intentionallyDisconnected) {
          this.updateStatus('error');
          this.updateMessage('Connection lost. Retrying…');
          this.scheduleReconnect();
        } else {
          this.updateStatus('disconnected');
          this.updateMessage(null);
        }
      };

      socket.onerror = () => {
        // onerror will be followed by onclose
      };
    } catch (e) {
      console.error('Failed to connect to WS', e);
      this.updateStatus('error');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.intentionallyDisconnected) return;
    if (this.reconnectTimer !== null) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect(this.url);
    }, this.reconnectInterval);
    // Exponential backoff
    this.reconnectInterval = Math.min(this.reconnectInterval * 2, this.maxReconnectInterval);
  }

  public disconnect(): void {
    this.intentionallyDisconnected = true;
    this.frameInFlight = false;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    const socket = this.ws;
    this.ws = null;
    if (socket) {
      socket.close();
    }
    this.updateStatus('disconnected');
  }

  public sendFrame(frame: CapturedFrame): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN && !this.frameInFlight) {
      this.frameInFlight = true;
      const sentAt = Date.now();
      if (TRACE_PIPELINE) console.log(`[PERCEPTA_TRACE] frame=${frame.id} ts=${sentAt} send_attempt`);
      const header = new TextEncoder().encode(`${frame.id}\n`);
      this.ws.send(new Blob([header, frame.blob], { type: 'application/octet-stream' }));
    } else if (TRACE_PIPELINE) {
      console.log(`[PERCEPTA_TRACE] stage=drop frame=${frame.id} ts=${Date.now()} reason=in_flight`);
    }
  }

  public sendVoiceCommand(command: string, transcript: string, confidence: number): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'voice',
        command,
        transcript,
        confidence,
        timestamp: Date.now()
      }));
    }
  }

  public sendSettings(settings: PercetpaSettings): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'settings',
        ...settings
      }));
    }
  }

  public sendModalities(faceEnabled: boolean, handEnabled: boolean, voiceEnabled: boolean): void {
    this.pendingModalities = { face: faceEnabled, hand: handEnabled, voice: voiceEnabled };
    this.sendPendingModalities();
  }

  private sendPendingModalities(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'modalities', face_enabled: this.pendingModalities.face, hand_enabled: this.pendingModalities.hand, voice_enabled: this.pendingModalities.voice }));
    }
  }

  public sendCalibrationAction(action: string, step: number): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'calibration',
        action,
        step
      }));
    }
  }

  public onPerception(cb: (result: PerceptionResult) => void): void {
    this.onPerceptionCallback = cb;
  }

  public onStatusChange(cb: (status: ConnectionStatus) => void): void {
    this.onStatusCallback = cb;
  }

  public onMessage(cb: (message: string | null) => void): void {
    this.onMessageCallback = cb;
  }

  private updateStatus(status: ConnectionStatus): void {
    if (this.onStatusCallback) {
      this.onStatusCallback(status);
    }
  }

  private updateMessage(message: string | null): void {
    if (this.onMessageCallback) {
      this.onMessageCallback(message);
    }
  }

  public get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

export const wsService = new PerceptaWSService();
