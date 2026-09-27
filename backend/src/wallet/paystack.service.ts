import {
  Injectable,
  InternalServerErrorException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createHmac, timingSafeEqual } from 'crypto';

const PAYSTACK_BASE_URL = 'https://api.paystack.co';

export interface PaystackInitializeResult {
  authorizationUrl: string;
  accessCode: string;
  reference: string;
}

export interface PaystackVerifyResult {
  status: string; // 'success', 'failed', 'abandoned', ...
  amountKobo: number;
  reference: string;
  currency: string;
}

// Thin wrapper around the Paystack REST API. There's no official Node SDK,
// so this just uses fetch (built into Node 20) rather than pulling in a
// dependency for a handful of endpoints.
@Injectable()
export class PaystackService {
  private readonly logger = new Logger(PaystackService.name);
  private readonly secretKey: string;

  constructor(private readonly configService: ConfigService) {
    this.secretKey = this.configService.getOrThrow<string>(
      'PAYSTACK_SECRET_KEY',
    );
  }

  async initializeTransaction(params: {
    email: string;
    amountKobo: number;
    reference: string;
    callbackUrl?: string;
  }): Promise<PaystackInitializeResult> {
    const response = await fetch(`${PAYSTACK_BASE_URL}/transaction/initialize`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.secretKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: params.email,
        amount: params.amountKobo,
        reference: params.reference,
        callback_url: params.callbackUrl,
      }),
    });

    const body = await response.json();

    if (!response.ok || !body.status) {
      this.logger.error(`Paystack initialize failed: ${JSON.stringify(body)}`);
      throw new InternalServerErrorException(
        'Could not start payment with Paystack',
      );
    }

    return {
      authorizationUrl: body.data.authorization_url,
      accessCode: body.data.access_code,
      reference: body.data.reference,
    };
  }

  async verifyTransaction(reference: string): Promise<PaystackVerifyResult> {
    const response = await fetch(
      `${PAYSTACK_BASE_URL}/transaction/verify/${encodeURIComponent(reference)}`,
      { headers: { Authorization: `Bearer ${this.secretKey}` } },
    );

    const body = await response.json();

    if (!response.ok || !body.status) {
      this.logger.error(`Paystack verify failed: ${JSON.stringify(body)}`);
      throw new InternalServerErrorException(
        'Could not verify payment with Paystack',
      );
    }

    return {
      status: body.data.status,
      amountKobo: body.data.amount,
      reference: body.data.reference,
      currency: body.data.currency,
    };
  }

  // Paystack signs every webhook body with HMAC-SHA512 using the secret key.
  // This must run against the exact raw request bytes - re-serializing the
  // parsed JSON would very likely produce a different signature.
  verifyWebhookSignature(rawBody: Buffer, signature: string | undefined): boolean {
    if (!signature) return false;

    const expected = createHmac('sha512', this.secretKey)
      .update(rawBody)
      .digest('hex');

    const expectedBuf = Buffer.from(expected, 'utf8');
    const signatureBuf = Buffer.from(signature, 'utf8');

    if (expectedBuf.length !== signatureBuf.length) return false;
    return timingSafeEqual(expectedBuf, signatureBuf);
  }
}
