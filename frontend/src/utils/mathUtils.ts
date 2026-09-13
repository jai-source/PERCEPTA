export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function formatConfidence(conf: number): string {
  return `${Math.round(conf * 100)}%`;
}

export function getGestureColor(gesture: string): string {
  if (gesture.includes('VOICE')) return 'var(--accent-purple)';
  if (gesture.includes('HAND')) return 'var(--accent-teal)';
  return 'var(--accent-primary)';
}

export function getModalityColor(modality: string): string {
  switch (modality) {
    case 'FACE': return 'var(--accent-primary)';
    case 'HAND': return 'var(--accent-teal)';
    case 'VOICE': return 'var(--accent-purple)';
    case 'SYSTEM': return 'var(--text-secondary)';
    default: return 'var(--text-primary)';
  }
}

export function formatEventType(eventType: string): string {
  return eventType
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}
