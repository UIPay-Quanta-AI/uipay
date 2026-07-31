/* eslint-disable @typescript-eslint/no-unsafe-assignment */
import {
  BadRequestException,
  ConflictException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service';
import { SignupUserDto } from './signup-user.dto';

import { RedisService } from '../../redis/redis.service';
import { hashPassword } from '../../common/crypto/password';
import { EmailQueueService } from '../../queue/email/email.service';
import { OtpService } from '../otp/otp.service';
import { cryptoHash, verifyHash } from '../../common/crypto/crypto';
import { SessionService } from '../session/session.service';
import { AppJwtService } from '../jwt/app-jwt.service';

export interface PendingRegistration {
  email: string;
  firstName: string;
  middleName?: string;
  lastName: string;
  dob: string;
  phoneNumber: string;
  passwordHash: string;
  otpHash: string;
}

@Injectable()
export class SignupUserService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly otpService: OtpService,
    private readonly redis: RedisService,
    private readonly emailQueueService: EmailQueueService,
    private readonly appJwtService: AppJwtService,
    private readonly sessionService: SessionService,
  ) {}

  private findByEmail(email: string) {
    return this.prisma.user.findUnique({
      where: {
        email,
      },
    });
  }

  async signupUser(body: SignupUserDto) {
    const email = body.emailAddress.toLowerCase().trim();
    const firstName = body.firstName.trim();
    const middleName = body.middleName?.trim();
    const lastName = body.lastName.trim();
    const dob = body.dob.trim();
    const phoneNumber = body.phoneNumber;

    const existingUser = await this.findByEmail(email);
    if (existingUser) {
      throw new ConflictException('Email already exists');
    }

    const hashedPassword = await hashPassword(body.password);

    const { otp, otpHash, ttlSeconds } = this.otpService.generateOtp();

    const pendingRegistration: PendingRegistration = {
      email,
      firstName,
      middleName,
      lastName,
      dob,
      phoneNumber,
      passwordHash: hashedPassword,
      otpHash,
    };

    await this.redis.client.del(`register:${email}`);
    await this.redis.client.set(
      `register:${email}`,
      JSON.stringify(pendingRegistration),
      'EX',
      ttlSeconds,
    );

    await this.emailQueueService.sendVerification(email, otp);

    return {
      message: 'Verification code sent successfully.',
    };
  }

  async verifyOtp(emailAddress: string, otp: string) {
    const email = emailAddress.toLowerCase().trim();

    if (!email) {
      throw new BadRequestException('Email address is required');
    }

    if (!otp || otp.length !== 6) {
      throw new BadRequestException('Invalid OTP');
    }

    const storedData = await this.redis.client.get(`register:${email}`);

    if (!storedData) {
      throw new UnauthorizedException(
        'OTP has expired or registration was not found',
      );
    }

    const pendingRegistration: PendingRegistration = JSON.parse(storedData);

    const verifyOtpCode = verifyHash(otp, pendingRegistration.otpHash);

    if (!verifyOtpCode) {
      throw new UnauthorizedException('Invalid OTP');
    }

    const user = await this.prisma.user.create({
      data: {
        email: pendingRegistration.email,
        firstName: pendingRegistration.firstName,
        middleName: pendingRegistration.middleName,
        lastName: pendingRegistration.lastName,
        dob: pendingRegistration.dob,
        phoneNumber: pendingRegistration.phoneNumber,
        passwordHash: pendingRegistration.passwordHash,
      },
    });

    const { accessToken, refreshToken } =
      await this.appJwtService.generateTokens({
        sub: user.id,
        email: user.email,
      });

    const refreshTokenHash = cryptoHash(refreshToken);

    await this.sessionService.createSession({
      userId: user.id,
      refreshTokenHash,
      expiresAt: this.appJwtService.getRefreshTokenExpiryDate(),
    });

    await this.redis.client.del(`register:${email}`);

    return {
      accessToken,
      refreshToken,
    };
  }
}
