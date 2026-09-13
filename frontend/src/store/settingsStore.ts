import { create } from 'zustand';
import { PercetpaSettings, DEFAULT_SETTINGS } from '../types/settings';
import { wsService } from '../services/PerceptaWSService';

interface SettingsState {
  settings: PercetpaSettings;
  updateSetting: <K extends keyof PercetpaSettings>(key: K, value: PercetpaSettings[K]) => void;
  resetToDefaults: () => void;
  sendToBackend: () => void;
}

// Load from local storage
const loadSettings = (): PercetpaSettings => {
  const saved = localStorage.getItem('percepta_settings');
  if (saved) {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
    } catch (e) {
      console.error('Failed to parse settings', e);
    }
  }
  return { ...DEFAULT_SETTINGS };
};

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: loadSettings(),
  
  updateSetting: (key, value) => {
    set((state) => {
      const newSettings = { ...state.settings, [key]: value };
      localStorage.setItem('percepta_settings', JSON.stringify(newSettings));
      return { settings: newSettings };
    });
  },
  
  resetToDefaults: () => {
    set({ settings: { ...DEFAULT_SETTINGS } });
    localStorage.removeItem('percepta_settings');
  },
  
  sendToBackend: () => {
    const { settings } = get();
    wsService.sendSettings(settings);
  }
}));
