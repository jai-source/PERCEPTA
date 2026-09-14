/// <reference lib="webworker" />
/**
 * Minimal dedicated worker that runs setInterval at a requested rate and
 * posts 'tick' messages back to the main thread.
 *
 * Chrome/Edge throttle setInterval/setTimeout on a page's MAIN thread to
 * roughly 1 call/sec once the tab is backgrounded (a battery-saving policy).
 * Timers running inside a Web Worker are NOT subject to this same clamp, so
 * moving the capture SCHEDULING here keeps frame capture running while the
 * user switches to a different browser tab (same window, tab still open).
 *
 * NOTE: This does NOT make gesture control work while the user has switched
 * to a completely different application outside the browser — that would
 * require a local companion desktop agent outside of browser sandboxing,
 * which is out of scope.
 */

let intervalId: number | null = null;

self.onmessage = (e: MessageEvent) => {
  const { type, intervalMs } = e.data || {};

  if (type === 'start') {
    if (intervalId !== null) {
      clearInterval(intervalId);
    }
    intervalId = self.setInterval(() => {
      self.postMessage('tick');
    }, intervalMs);
  } else if (type === 'stop') {
    if (intervalId !== null) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }
};