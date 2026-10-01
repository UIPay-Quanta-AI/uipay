import {
  BadGatewayException,
  HttpException,
  Injectable,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { randomUUID } from 'crypto';
import { PrismaService } from '../prisma/prisma.service';

interface CallContext {
  userId: string;
  sessionId: string;
  locale?: string;
}

// Trusted identity headers Quanta requires on every call (see
// quanta/docs/proxy-integration-contract.md). Quanta never takes user
// identity from the LLM or the request body - only from these headers,
// which we set here after having already verified the real user's JWT.
function buildHeaders(ctx: CallContext, extra: Record<string, string> = {}) {
  return {
    'X-User-ID': ctx.userId,
    'X-Session-ID': ctx.sessionId,
    'X-Request-ID': randomUUID(),
    ...(ctx.locale ? { 'X-Locale': ctx.locale } : {}),
    ...extra,
  };
}

// Buffer's type declares an ArrayBufferLike backing store (which includes
// SharedArrayBuffer), but Blob only accepts a concrete ArrayBuffer - copying
// into a fresh Uint8Array satisfies that without changing the bytes.
function toBlob(buffer: Uint8Array, mimetype: string): Blob {
  return new Blob([new Uint8Array(buffer)], { type: mimetype });
}

@Injectable()
export class QuantaProxyService {
  constructor(
    private readonly config: ConfigService,
    private readonly prisma: PrismaService,
  ) {}

  private get baseUrl(): string {
    return this.config.getOrThrow<string>('QUANTA_BASE_URL');
  }

  // Quanta never persists the voice profile itself (see voiceEnroll below),
  // so this table is the only real source of truth for "is this user
  // enrolled" - not a client-side guess.
  async voiceStatus(userId: string) {
    const profile = await this.prisma.voiceProfile.findUnique({ where: { userId } });
    return { enrolled: !!profile };
  }

  private async forward(path: string, init: RequestInit): Promise<unknown> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, init);
    } catch {
      throw new BadGatewayException('Could not reach Quanta service');
    }

    const body = await response.json().catch(() => null);

    if (!response.ok) {
      // Relay Quanta's own status/detail rather than flattening everything
      // to a generic 500 - the frontend needs to tell "bad input" (4xx)
      // apart from "Quanta is down" (5xx/502).
      throw new HttpException(body ?? 'Quanta request failed', response.status);
    }

    return body;
  }

  async interact(
    ctx: CallContext,
    body: { text?: string; verification_threshold?: number; metadata?: Record<string, unknown> },
  ) {
    return this.forward('/api/v1/interact', {
      method: 'POST',
      headers: { ...buildHeaders(ctx), 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  async interactMultipart(
    ctx: CallContext,
    fields: {
      text?: string;
      verification_threshold?: number;
      image?: { buffer: Buffer; filename: string; mimetype: string };
      audio?: { buffer: Buffer; filename: string; mimetype: string };
      voice_profile?: { buffer: Buffer; filename: string; mimetype: string };
    },
  ) {
    const form = new FormData();
    if (fields.text !== undefined) form.append('text', fields.text);
    if (fields.verification_threshold !== undefined) {
      form.append('verification_threshold', String(fields.verification_threshold));
    }
    if (fields.image) {
      form.append(
        'image',
        toBlob(fields.image.buffer, fields.image.mimetype),
        fields.image.filename,
      );
    }
    if (fields.audio) {
      form.append(
        'audio',
        toBlob(fields.audio.buffer, fields.audio.mimetype),
        fields.audio.filename,
      );
    }
    if (fields.voice_profile) {
      form.append(
        'voice_profile',
        toBlob(fields.voice_profile.buffer, fields.voice_profile.mimetype),
        fields.voice_profile.filename,
      );
    }

    return this.forward('/api/v1/interact/multipart', {
      method: 'POST',
      headers: buildHeaders(ctx),
      body: form,
    });
  }

  // Automatically attaches the user's stored voice profile (if enrolled) -
  // per the enrollment contract, Quanta doesn't persist it, so the proxy is
  // the source of truth for it on every subsequent voice turn.
  async voiceInteract(
    ctx: CallContext,
    audio: { buffer: Buffer; filename: string; mimetype: string },
    verificationThreshold?: number,
  ) {
    const storedProfile = await this.prisma.voiceProfile.findUnique({
      where: { userId: ctx.userId },
    });

    const form = new FormData();
    form.append('audio', toBlob(audio.buffer, audio.mimetype), audio.filename);
    if (storedProfile) {
      form.append(
        'voice_profile',
        toBlob(storedProfile.encryptedBlob, 'application/octet-stream'),
        'voice_profile.bin',
      );
    }
    if (verificationThreshold !== undefined) {
      form.append('verification_threshold', String(verificationThreshold));
    }

    return this.forward('/api/v1/voice/interact', {
      method: 'POST',
      headers: buildHeaders(ctx),
      body: form,
    });
  }

  async voiceEnroll(ctx: CallContext, audio: { buffer: Buffer; filename: string; mimetype: string }) {
    const form = new FormData();
    form.append('audio', toBlob(audio.buffer, audio.mimetype), audio.filename);

    const result = (await this.forward('/api/v1/voice/enroll', {
      method: 'POST',
      headers: buildHeaders(ctx),
      body: form,
    })) as { profile_base64?: string | null; complete: boolean; [key: string]: unknown };

    if (result.complete && result.profile_base64) {
      const blob = Buffer.from(result.profile_base64, 'base64');
      await this.prisma.voiceProfile.upsert({
        where: { userId: ctx.userId },
        update: { encryptedBlob: blob },
        create: { userId: ctx.userId, encryptedBlob: blob },
      });
    }

    return result;
  }
}
