class VoiceService {
  private recognition: any = null;
  private isListening = false;
  private onCommandCallback: ((command: string, transcript: string, confidence: number) => void) | null = null;
  private onListeningChangeCallback: ((listening: boolean) => void) | null = null;

  private readonly COMMAND_MAP: Record<string, string> = {
    'click': 'VOICE_CLICK',
    'double click': 'VOICE_DOUBLE_CLICK',
    'right click': 'VOICE_RIGHT_CLICK',
    'scroll up': 'VOICE_SCROLL_UP',
    'scroll down': 'VOICE_SCROLL_DOWN',
    'go left': 'VOICE_GO_LEFT',
    'go right': 'VOICE_GO_RIGHT',
    'go up': 'VOICE_GO_UP',
    'go down': 'VOICE_GO_DOWN',
    'go back': 'VOICE_GO_BACK',
    'go forward': 'VOICE_GO_FORWARD',
    'pause': 'VOICE_PAUSE',
    'resume': 'VOICE_RESUME',
    'recalibrate': 'VOICE_RECALIBRATE',
    'stop': 'VOICE_STOP'
  };

  constructor() {
    // @ts-ignore
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-US';

      this.recognition.onresult = (event: any) => {
        const lastResult = event.results[event.results.length - 1];
        const transcript = lastResult[0].transcript.trim().toLowerCase();
        const confidence = lastResult[0].confidence;
        
        // Match against known commands
        for (const [key, command] of Object.entries(this.COMMAND_MAP)) {
          if (transcript.includes(key)) {
            if (this.onCommandCallback) {
              this.onCommandCallback(command, transcript, confidence);
            }
            break; // Stop matching after first find
          }
        }
      };

      this.recognition.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
        if (event.error === 'not-allowed') {
          this.setListening(false);
        }
      };

      this.recognition.onend = () => {
        if (this.isListening) {
          // Restart if it stopped but we still want to listen
          try {
            this.recognition.start();
          } catch (e) {
            console.error('Failed to restart speech recognition', e);
          }
        }
      };
    }
  }

  public isSupported(): boolean {
    return this.recognition !== null;
  }

  public start(): void {
    if (this.recognition && !this.isListening) {
      try {
        this.recognition.start();
        this.setListening(true);
      } catch (e) {
        console.error('Failed to start speech recognition', e);
      }
    }
  }

  public stop(): void {
    if (this.recognition && this.isListening) {
      this.isListening = false;
      this.setListening(false);
      this.recognition.stop();
    }
  }

  public onCommand(cb: (command: string, transcript: string, confidence: number) => void): void {
    this.onCommandCallback = cb;
  }

  public onListeningChange(cb: (listening: boolean) => void): void {
    this.onListeningChangeCallback = cb;
  }

  private setListening(listening: boolean): void {
    this.isListening = listening;
    if (this.onListeningChangeCallback) {
      this.onListeningChangeCallback(listening);
    }
  }
}

export const voiceService = new VoiceService();
