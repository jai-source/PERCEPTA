import { create } from 'zustand';
import { EventLogEntry, PerceptualEvent } from '../types/events';

interface EventState {
  events: EventLogEntry[];
  maxEvents: number;
  totalEventsCount: number;
  eventCounts: Record<string, number>;
  
  addEvents: (events: PerceptualEvent[]) => void;
  addVoiceEvent: (command: string, confidence: number) => void;
  clearEvents: () => void;
}

function formatTimestamp(ts: number): string {
  const d = new Date(ts);
  return d.toTimeString().split(' ')[0];
}

export const useEventStore = create<EventState>((set) => ({
  events: [],
  maxEvents: 200,
  totalEventsCount: 0,
  eventCounts: {},

  addEvents: (newEvents) => set((state) => {
    const formattedEvents = newEvents.map(e => ({
      ...e,
      id: `${e.timestamp}-${Math.random().toString(36).substring(2, 9)}`,
      formatted_time: formatTimestamp(e.timestamp)
    }));
    
    const combined = [...state.events, ...formattedEvents];
    if (combined.length > state.maxEvents) {
      combined.splice(0, combined.length - state.maxEvents);
    }
    
    const newCounts = { ...state.eventCounts };
    newEvents.forEach(e => {
      newCounts[e.event_type] = (newCounts[e.event_type] || 0) + 1;
    });

    return {
      events: combined,
      totalEventsCount: state.totalEventsCount + newEvents.length,
      eventCounts: newCounts
    };
  }),

  addVoiceEvent: (command, confidence) => set((state) => {
    const e: EventLogEntry = {
      event_type: `VOICE_${command.toUpperCase().replace(/\s+/g, '_')}`,
      modality: 'VOICE',
      confidence,
      timestamp: Date.now(),
      payload: { command },
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      formatted_time: formatTimestamp(Date.now())
    };
    
    const combined = [...state.events, e];
    if (combined.length > state.maxEvents) {
      combined.splice(0, combined.length - state.maxEvents);
    }
    
    const newCounts = { ...state.eventCounts };
    newCounts[e.event_type] = (newCounts[e.event_type] || 0) + 1;

    return {
      events: combined,
      totalEventsCount: state.totalEventsCount + 1,
      eventCounts: newCounts
    };
  }),

  clearEvents: () => set({ events: [], eventCounts: {}, totalEventsCount: 0 })
}));
