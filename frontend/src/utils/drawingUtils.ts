import { BoundingBox, Keypoint } from '../types/perception';

export function drawFaceBoundingBox(ctx: CanvasRenderingContext2D, bbox: BoundingBox, color: string, label: string): void {
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.shadowColor = color;
  ctx.shadowBlur = 10;
  
  // Draw rounded rect manually or just rect
  ctx.beginPath();
  ctx.roundRect(bbox.x, bbox.y, bbox.w, bbox.h, 8);
  ctx.stroke();
  
  // Reset shadow for text
  ctx.shadowBlur = 0;
  
  // Label background
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(bbox.x, bbox.y - 24, ctx.measureText(label).width + 16, 24, [8, 8, 0, 0]);
  ctx.fill();
  
  // Text
  ctx.fillStyle = '#ffffff';
  ctx.font = '12px Inter';
  ctx.fillText(label, bbox.x + 8, bbox.y - 8);
}

export function drawHandBoundingBox(ctx: CanvasRenderingContext2D, bbox: BoundingBox, color: string, label: string): void {
  drawFaceBoundingBox(ctx, bbox, color, label); // Reuse same style
}

export function drawKeypoints(ctx: CanvasRenderingContext2D, keypoints: Keypoint[], color: string): void {
  ctx.fillStyle = color;
  ctx.shadowColor = color;
  ctx.shadowBlur = 4;
  
  keypoints.forEach(kp => {
    ctx.beginPath();
    ctx.arc(kp.x, kp.y, 3, 0, 2 * Math.PI);
    ctx.fill();
  });
  
  ctx.shadowBlur = 0;
}

export function drawHeadVector(ctx: CanvasRenderingContext2D, nose: {x: number, y: number}, dx: number, dy: number): void {
  const scale = 50; // visual scale for vector
  ctx.strokeStyle = '#f59e0b';
  ctx.lineWidth = 3;
  
  ctx.beginPath();
  ctx.moveTo(nose.x, nose.y);
  ctx.lineTo(nose.x + dx * scale, nose.y + dy * scale);
  ctx.stroke();
}

export function drawGestureLabel(ctx: CanvasRenderingContext2D, x: number, y: number, label: string, confidence: number, color: string): void {
  const text = `${label} (${Math.round(confidence * 100)}%)`;
  ctx.fillStyle = color;
  ctx.font = 'bold 16px Inter';
  ctx.fillText(text, x, y);
}

export function clearCanvas(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  ctx.clearRect(0, 0, width, height);
}
