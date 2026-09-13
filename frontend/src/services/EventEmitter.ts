class EventEmitter<T extends Record<string, unknown>> {
  private events: Map<keyof T, Function[]> = new Map();

  public on<K extends keyof T>(event: K, callback: (data: T[K]) => void): void {
    const callbacks = this.events.get(event) || [];
    callbacks.push(callback);
    this.events.set(event, callbacks);
  }

  public off<K extends keyof T>(event: K, callback: (data: T[K]) => void): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      this.events.set(
        event,
        callbacks.filter((cb) => cb !== callback)
      );
    }
  }

  public emit<K extends keyof T>(event: K, data: T[K]): void {
    const callbacks = this.events.get(event);
    if (callbacks) {
      callbacks.forEach((cb) => cb(data));
    }
  }
}

export default EventEmitter;
