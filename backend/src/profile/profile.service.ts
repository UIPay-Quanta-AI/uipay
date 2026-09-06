import { Injectable } from '@nestjs/common';
import { hashPassword } from '../common/crypto/password';
import { PrismaService } from '../prisma/prisma.service';
import { SetPinDto, VerifyIdDto } from './profile.dto';

@Injectable()
export class ProfileService {
  constructor(private readonly prisma: PrismaService) {}

  async getMe(userId: string) {
    const user = await this.prisma.user.findUniqueOrThrow({
      where: { id: userId },
      select: {
        firstName: true,
        middleName: true,
        lastName: true,
        dob: true,
        email: true,
        phoneNumber: true,
        idType: true,
        identityVerifiedAt: true,
        transactionPinHash: true,
      },
    });

    const { transactionPinHash, ...rest } = user;
    return { ...rest, hasTransactionPin: transactionPinHash !== null };
  }

  async setPin(userId: string, dto: SetPinDto) {
    const transactionPinHash = await hashPassword(dto.pin);

    await this.prisma.user.update({
      where: { id: userId },
      data: { transactionPinHash },
    });

    return { hasTransactionPin: true };
  }

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
