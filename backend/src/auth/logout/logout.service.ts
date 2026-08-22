import { Injectable } from '@nestjs/common';
import { cryptoHash } from '../../common/crypto/crypto';
import { SessionService } from '../session/session.service';

@Injectable()
export class LogoutService {
  constructor(private readonly sessionService: SessionService) {}

  async logout(refreshToken: string) {
    const refreshTokenHash = cryptoHash(refreshToken);

    await this.sessionService.deleteByRefreshTokenHash(refreshTokenHash);
  }
}
