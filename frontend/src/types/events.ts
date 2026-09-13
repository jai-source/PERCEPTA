export interface PerceptualEvent {
  event_type: string;
  modality: 'FACE' | 'HAND' | 'VOICE' | 'SYSTEM';
  confidence: number;
  timestamp: number;
  payload: Record<string, unknown>;
}

export interface EventLogEntry extends PerceptualEvent {
  id: string;
  formatted_time: string;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'initializing' | 'error';
