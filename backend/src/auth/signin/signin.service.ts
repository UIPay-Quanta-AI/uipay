import {
  ForbiddenException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service';
import { SignInDto } from './signin.dto';
import { comparePassword } from '../../common/crypto/password';
import { AppJwtService } from '../jwt/app-jwt.service';
import { SessionService } from '../session/session.service';
import { cryptoHash } from '../../common/crypto/crypto';

interface DeviceInfo {
  userAgent?: string;
  ipAddress?: string;
}

@Injectable()
export class SignInService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly appJwtService: AppJwtService,
    private readonly sessionService: SessionService,
  ) {}

  async signIn(body: SignInDto, device: DeviceInfo = {}) {
    const email = body.email.trim().toLowerCase();

    const user = await this.prisma.user.findUnique({
      where: { email },
    });

    if (!user) {
      throw new UnauthorizedException('Invalid email or password');
    }

    const isPasswordValid = await comparePassword(
      body.password,
      user.passwordHash,
    );

    if (!isPasswordValid) {
      throw new UnauthorizedException('Invalid email or password');
    }

    if (user.status === 'suspended') {
      throw new ForbiddenException(
        'This account has been suspended. Contact support for help.',
      );
    }

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
      userAgent: device.userAgent,
      ipAddress: device.ipAddress,
    });

    return {
      accessToken,
      refreshToken,
    };
  }
}
