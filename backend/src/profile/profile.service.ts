import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { VerifyIdDto } from './profile.dto';

@Injectable()
export class ProfileService {
  constructor(private readonly prisma: PrismaService) {}

  async verifyId(userId: string, dto: VerifyIdDto) {
    // there's no real BVN/NIN lookup provider wired up yet, so this just
    // records the number and marks the profile as identity verified
    return this.prisma.user.update({
      where: { id: userId },
      data: {
        idType: dto.idType,
        idNumber: dto.idNumber,
        identityVerifiedAt: new Date(),
      },
      select: {
        id: true,
        idType: true,
        identityVerifiedAt: true,
      },
    });
  }
}
