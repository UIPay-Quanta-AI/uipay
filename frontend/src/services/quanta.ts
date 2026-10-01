import api from '@/services/api';

export interface QuantaSpeech {
  text: string;
}

export interface QuantaResponse {
  request_id: string;
  status:
    | 'success'
    | 'clarification_required'
    | 'input_required'
    | 'confirmation_required'
    | 'processing'
    | 'cancelled'
    | 'error';
  speech: QuantaSpeech | null;
  ui: { type: string };
  data: Record<string, unknown> | null;
  error: { code: string; message: string } | null;
  response_language: string;
}

export interface VoicePipelineResult {
  outcome:
    | 'success'
    | 'verification_unavailable'
    | 'verification_failed'
    | 'transcription_failed';
  verification: { verified: boolean; score: number; threshold: number } | null;
  transcript: { text: string; language: string } | null;
  response: QuantaResponse | null;
  error: string | null;
}

export interface VoiceEnrollmentResponse {
  complete: boolean;
  percent_complete: number;
  profile_available: boolean;
  message: string;
}

// Shape of QuantaResponse.data when ui.type is "transfer_confirmation" -
// mirrors quanta/app/schemas/transfer.py's TransferPreparation, produced by
// the prepare_transfer tool. beneficiary_id is OUR beneficiaries.id, not
// the recipient's user id - it still has to be resolved to a real UIPay
// account before anything can be paid.
export interface TransferPreparationData {
  reference: string;
  beneficiary_id: string;
  amount: number;
  currency: string;
}

export interface ResolvedTransferRecipient {
  recipientId: string;
  name: string;
  accountNumber: string;
}

// Shape of QuantaResponse.data when status is "input_required" and
// ui.type is "beneficiary_selection" with an empty list - the deterministic
// fallback the orchestrator returns when search_beneficiary finds no match
// for the name Quanta heard (see quanta/app/orchestration/orchestrator.py).
export interface BeneficiaryNotFoundData {
  name_heard: string;
  beneficiaries: unknown[];
}

// Quanta only ever proposes a transfer - it never moves money itself. This
// resolves its proposal (a beneficiary_id) into a real, payable UIPay
// account the same way manual "Add Beneficiary" does, so the existing
// confirm/PIN/transfer screens can take over from here unchanged.
export async function resolveTransferBeneficiary(
  beneficiaryId: string,
): Promise<ResolvedTransferRecipient> {
  const beneficiariesRes = await api.get('/beneficiaries');
  const beneficiaries: { id: string; accountNumber: string }[] =
    beneficiariesRes.data.data;
  const beneficiary = beneficiaries.find((b) => b.id === beneficiaryId);
  if (!beneficiary) {
    throw new Error("That saved recipient couldn't be found anymore.");
  }

  const resolveRes = await api.get(`/wallet/resolve/${beneficiary.accountNumber}`);
  const { userId, accountName } = resolveRes.data.data;

  return {
    recipientId: userId,
    name: accountName,
    accountNumber: beneficiary.accountNumber,
  };
}

// crypto.randomUUID() needs a secure context (https/localhost) - same
// restriction that blocks getUserMedia on a plain http LAN address. This
// id only needs to be unique, not cryptographically random, so a
// Math.random fallback is fine when that API isn't available.
function generateId(): string {
  if (window.isSecureContext && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

// A stable per-tab conversation id so Quanta's SessionManager can track a
// multi-turn conversation (partial transfers, follow-up questions) instead
// of starting fresh on every request.
function getSessionId(): string {
  const KEY = 'quanta_session_id';
  let id = sessionStorage.getItem(KEY);
  if (!id) {
    id = generateId();
    sessionStorage.setItem(KEY, id);
  }
  return id;
}

function audioExtension(mimeType: string): string {
  if (mimeType.includes('webm')) return 'webm';
  if (mimeType.includes('ogg')) return 'ogg';
  if (mimeType.includes('mp4')) return 'm4a';
  if (mimeType.includes('wav')) return 'wav';
  return 'webm';
}

export async function quantaInteract(
  text: string,
  locale: string,
): Promise<QuantaResponse> {
  const res = await api.post(
    '/quanta/interact',
    { text },
    { headers: { 'X-Session-ID': getSessionId(), 'Accept-Language': locale } },
  );
  return res.data;
}

export async function quantaVoiceInteract(
  audio: Blob,
  locale: string,
): Promise<VoicePipelineResult> {
  const form = new FormData();
  form.append('audio', audio, `turn.${audioExtension(audio.type)}`);

  const res = await api.post('/quanta/voice/interact', form, {
    headers: { 'X-Session-ID': getSessionId(), 'Accept-Language': locale },
  });
  return res.data;
}

export async function quantaVoiceEnroll(audio: Blob): Promise<VoiceEnrollmentResponse> {
  const form = new FormData();
  form.append('audio', audio, `sample.${audioExtension(audio.type)}`);

  const res = await api.post('/quanta/voice/enroll', form, {
    headers: { 'X-Session-ID': getSessionId() },
  });
  return res.data;
}

export async function quantaVoiceStatus(): Promise<{ enrolled: boolean }> {
  const res = await api.get('/quanta/voice/status');
  return res.data;
}
