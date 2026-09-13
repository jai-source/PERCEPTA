export interface BoundingBox { x: number; y: number; w: number; h: number; }
export interface Keypoint { x: number; y: number; conf: number; }

export interface FaceDetection {
  detected: boolean;
  bbox: BoundingBox | null;
  keypoints: Keypoint[];
  gesture: string | null;
  confidence: number;
  head_pose: { dx: number; dy: number; tilt: number } | null;
}

export interface HandDetection {
  detected: boolean;
  bbox: BoundingBox | null;
  keypoints: Keypoint[];
  gesture: string | null;
  confidence: number;
  gesture_state: string;
}

export interface CursorPosition { x: number; y: number; }

export interface PerceptionResult {
  type: 'perception';
  trace_frame_id?: string | number;
  face: FaceDetection;
  hand: HandDetection;
  events: any[]; // will import PerceptualEvent
  cursor: CursorPosition;
  active_user_id: number;
  multi_user_detected: boolean;
  tracking_locked: boolean;
  fps: number;
  device: 'CUDA' | 'CPU';
  model_name: string;
  inference_ms: number;
  hand_model?: { name: string; loaded: boolean; error: string | null };
  face_model?: { name: string; loaded: boolean; error: string | null };
}
