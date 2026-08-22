import { Injectable } from '@nestjs/common';
import { PrismaService } from '../../prisma/prisma.service';
import { CreateSessionDto } from './session.dto';

@Injectable()
export class SessionService {
  constructor(private readonly prisma: PrismaService) {}

  async createSession(data: CreateSessionDto) {
    return this.prisma.session.create({
      data,
    });
  }

  async findByRefreshTokenHash(refreshTokenHash: string) {
    return this.prisma.session.findFirst({
      where: { refreshTokenHash },
    });
  }

  async deleteByRefreshTokenHash(refreshTokenHash: string) {
    await this.prisma.session.deleteMany({
      where: { refreshTokenHash },
    });
  }

  async deleteAllForUser(userId: string) {
    await this.prisma.session.deleteMany({
      where: { userId },
    });
  }
}
