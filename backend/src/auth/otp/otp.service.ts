import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { randomInt } from 'node:crypto';
import { cryptoHash } from '../../common/crypto/crypto';

@Injectable()
export class OtpService {
  constructor(private readonly configService: ConfigService) {}

  generateOtp() {
    const otp = randomInt(100000, 1000000).toString();
    const otpHash = cryptoHash(otp);

    const ttlSeconds = this.configService.getOrThrow<number>('OTP_EXPIRY');

    const expiresAt = new Date(Date.now() + ttlSeconds * 1000);

    return {
      otp,
      otpHash,
      ttlSeconds,
      expiresAt,
    };
  }
}
