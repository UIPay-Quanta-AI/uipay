import {
  Injectable,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service';
import { RedisService } from '../../redis/redis.service';
import { hashPassword } from '../../common/crypto/password';
import { verifyHash } from '../../common/crypto/crypto';
import { EmailQueueService } from '../../queue/email/email.service';
import { OtpService } from '../otp/otp.service';
import { SessionService } from '../session/session.service';
import { ForgotPasswordDto, ResetPasswordDto } from './forgot-password.dto';

@Injectable()
export class ForgotPasswordService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly otpService: OtpService,
    private readonly redis: RedisService,
    private readonly emailQueueService: EmailQueueService,
    private readonly sessionService: SessionService,
  ) {}

  private redisKey(email: string) {
    return `reset-password:${email}`;
  }

  async forgotPassword(dto: ForgotPasswordDto) {
    const email = dto.email.trim().toLowerCase();

    const user = await this.prisma.user.findUnique({ where: { email } });
    if (!user) {
      throw new NotFoundException('No account found with that email');
    }

    const { otp, otpHash, ttlSeconds } = this.otpService.generateOtp();

    await this.redis.client.del(this.redisKey(email));
    await this.redis.client.set(
      this.redisKey(email),
      otpHash,
      'EX',
      ttlSeconds,
    );

    await this.emailQueueService.sendPasswordReset(email, otp);
  }

  async resetPassword(dto: ResetPasswordDto) {
    const email = dto.email.trim().toLowerCase();

    const storedHash = await this.redis.client.get(this.redisKey(email));
    if (!storedHash) {
      throw new UnauthorizedException('OTP has expired or was not requested');
    }

    const isValidOtp = verifyHash(dto.otp, storedHash);
    if (!isValidOtp) {
      throw new UnauthorizedException('Invalid OTP');
    }

    const user = await this.prisma.user.findUnique({ where: { email } });
    if (!user) {
      throw new NotFoundException('No account found with that email');
    }

    const passwordHash = await hashPassword(dto.newPassword);

    await this.prisma.user.update({
      where: { email },
      data: { passwordHash },
    });

    // password just changed, so log every device out and make them sign in again
    await this.sessionService.deleteAllForUser(user.id);

    await this.redis.client.del(this.redisKey(email));
  }
}
