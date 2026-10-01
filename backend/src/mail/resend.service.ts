import {
  Injectable,
  InternalServerErrorException,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Resend } from 'resend';

@Injectable()
export class ResendService {
  private readonly logger = new Logger(ResendService.name);
  private readonly resend: Resend;
  constructor(private readonly configService: ConfigService) {
    this.resend = new Resend(
      this.configService.getOrThrow<string>('RESEND_API_KEY'),
    );
  }

  async sendOtpEmail(to: string, otp: string) {
    const from = this.configService.getOrThrow<string>('EMAIL_FROM');

    const { data, error } = await this.resend.emails.send({
      from,
      to,
      subject: 'Confirm your uipay account',
      html: `
  <h2>Verify your email</h2>
  <p>Thanks for signing up for Uipay.</p>
 <p>Your verification code is:</p>
<h1>${otp}</h1>
<p>This code expires in ${this.otpExpiryMinutes()} minutes.</p>
<p>If you didn't request this, you can ignore this email.</p>
    `,
    });

    if (error) {
      this.logger.error(error);
      throw new InternalServerErrorException(
        'Failed to send verification email',
      );
    }

    return data;
  }

  async sendPasswordResetOtpEmail(to: string, otp: string) {
    const from = this.configService.getOrThrow<string>('EMAIL_FROM');

    const { data, error } = await this.resend.emails.send({
      from,
      to,
      subject: 'Reset your uipay password',
      html: `
  <h2>Reset your password</h2>
  <p>We got a request to reset your uipay password.</p>
 <p>Your reset code is:</p>
<h1>${otp}</h1>
<p>This code expires in ${this.otpExpiryMinutes()} minutes.</p>
<p>If you didn't request this, you can ignore this email, your password stays the same.</p>
    `,
    });

    if (error) {
      this.logger.error(error);
      throw new InternalServerErrorException(
        'Failed to send password reset email',
      );
    }

    return data;
  }

  // Reads the same OTP_EXPIRY the backend actually enforces (see
  // OtpService.generateOtp), rather than a hardcoded number, so this text
  // can never drift out of sync with the real expiry again.
  private otpExpiryMinutes(): number {
    const seconds = this.configService.getOrThrow<number>('OTP_EXPIRY');
    return Math.round(seconds / 60);
  }
}
