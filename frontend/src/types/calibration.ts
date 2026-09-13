export interface CalibrationStep {
  step: number;
  name: string;
  description: string;
  instruction: string;
  status: 'pending' | 'detecting' | 'confirmed' | 'failed';
}

export interface CalibrationState {
  isActive: boolean;
  currentStep: number;
  steps: CalibrationStep[];
  isComplete: boolean;
}
