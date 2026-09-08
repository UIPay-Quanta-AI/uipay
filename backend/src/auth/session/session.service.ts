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

  async findAllForUser(userId: string) {
    return this.prisma.session.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
    });
  }

  // also filter by userId, so nobody can revoke another person's session
  // just by guessing the id
  async deleteOneForUser(userId: string, sessionId: string) {
    await this.prisma.session.deleteMany({
      where: { id: sessionId, userId },
    });
  }
}
