// Mirrors quanta/app/providers/tts/voices.py's DEFAULT_VOICES table - keep
// these two in sync if Quanta adds/removes a language or gender.
export const VOICE_LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'ha', label: 'Hausa' },
  { code: 'ig', label: 'Igbo' },
  { code: 'yo', label: 'Yoruba' },
  { code: 'pcm', label: 'Pidgin' },
] as const;

export type VoiceLanguage = (typeof VOICE_LANGUAGES)[number]['code'];
export type VoiceGender = 'female' | 'male';

export interface VoicePreference {
  language: VoiceLanguage;
  gender: VoiceGender;
}

const STORAGE_KEY = 'quanta_voice_preference';
const DEFAULT_PREFERENCE: VoicePreference = { language: 'en', gender: 'female' };

export function getVoicePreference(): VoicePreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFERENCE;
    const parsed = JSON.parse(raw);
    if (
      VOICE_LANGUAGES.some((l) => l.code === parsed.language) &&
      (parsed.gender === 'female' || parsed.gender === 'male')
    ) {
      return parsed;
    }
    return DEFAULT_PREFERENCE;
  } catch {
    return DEFAULT_PREFERENCE;
  }
}

export function setVoicePreference(pref: VoicePreference): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(pref));
  } catch {
    // best-effort only - a blocked/unavailable localStorage just means the
    // preference doesn't persist across visits, nothing else breaks
  }
}
