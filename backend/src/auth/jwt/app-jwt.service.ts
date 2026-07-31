import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { JwtPayload } from './jwt-payload.interface';
import ms, { StringValue } from 'ms';

@Injectable()
export class AppJwtService {
  constructor(
    private readonly jwt: JwtService,
    private readonly config: ConfigService,
  ) {}
  private async generateAccessToken(payload: JwtPayload) {
    return this.jwt.signAsync(payload, {
      secret: this.config.getOrThrow<string>('JWT_ACCESS_SECRET'),
      expiresIn: this.config.getOrThrow<StringValue>('JWT_ACCESS_EXPIRY'),
      issuer: this.config.getOrThrow<string>('APP_NAME'),
      audience: this.config.getOrThrow<string>('JWT_AUDIENCE'),
    });
  }

  private async generateRefreshToken(payload: JwtPayload) {
    return this.jwt.signAsync(payload, {
      secret: this.config.getOrThrow<string>('JWT_REFRESH_SECRET'),
      expiresIn: this.config.getOrThrow<StringValue>('JWT_REFRESH_EXPIRY'),
      issuer: this.config.getOrThrow<string>('APP_NAME'),
      audience: this.config.getOrThrow<string>('JWT_AUDIENCE'),
    });
  }

  async generateTokens(payload: JwtPayload) {
    const [accessToken, refreshToken] = await Promise.all([
      this.generateAccessToken(payload),
      this.generateRefreshToken(payload),
    ]);

    return {
      accessToken,
      refreshToken,
    };
  }

  getRefreshTokenExpiryDate(): Date {
    const expiresIn = this.config.getOrThrow<StringValue>('JWT_REFRESH_EXPIRY');

    return new Date(Date.now() + ms(expiresIn));
  }
}
