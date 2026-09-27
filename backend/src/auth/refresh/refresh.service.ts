import {
  ForbiddenException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service';
import { cryptoHash } from '../../common/crypto/crypto';
import { AppJwtService } from '../jwt/app-jwt.service';
import { SessionService } from '../session/session.service';

@Injectable()
export class RefreshService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly sessionService: SessionService,
    private readonly appJwtService: AppJwtService,
  ) {}

  async refresh(refreshToken: string) {
    const refreshTokenHash = cryptoHash(refreshToken);

    const session =
      await this.sessionService.findByRefreshTokenHash(refreshTokenHash);
    if (!session) {
      throw new UnauthorizedException('Invalid refresh token');
    }

    if (session.expiresAt < new Date()) {
      // session has expired already, no reason to keep the row around
      await this.sessionService.deleteByRefreshTokenHash(refreshTokenHash);
      throw new UnauthorizedException(
        'Refresh token expired, please sign in again',
      );
    }

    const user = await this.prisma.user.findUnique({
      where: { id: session.userId },
    });
    if (!user) {
      throw new UnauthorizedException('Invalid refresh token');
    }

    if (user.status === 'suspended') {
      await this.sessionService.deleteByRefreshTokenHash(refreshTokenHash);
      throw new ForbiddenException(
        'This account has been suspended. Contact support for help.',
      );
    }

    const accessToken = await this.appJwtService.generateAccessToken({
      sub: user.id,
      email: user.email,
    });

    return { accessToken };
  }
}
