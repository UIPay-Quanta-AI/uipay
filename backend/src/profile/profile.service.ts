import {
  Injectable,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { SessionService } from '../auth/session/session.service';
import { comparePassword, hashPassword } from '../common/crypto/password';
import { PrismaService } from '../prisma/prisma.service';
import {
  ChangePasswordDto,
  DeleteAccountDto,
  SetPinDto,
  UpdateNotificationPreferencesDto,
  UpdateProfileDto,
  VerifyIdDto,
  VerifyPinDto,
} from './profile.dto';

@Injectable()
export class ProfileService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly sessionService: SessionService,
  ) {}

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

  // Email and date of birth are deliberately not editable here - email is
  // the account's identity/login, and dob is tied to the verified-ID flow
  // (profile-setup/verify-id). Only the fields actually sent are touched,
  // so a partial edit never blanks the others.
  async updateProfile(userId: string, dto: UpdateProfileDto) {
    return this.prisma.user.update({
      where: { id: userId },
      data: dto,
      select: {
        firstName: true,
        lastName: true,
        phoneNumber: true,
      },
    });
  }

  async setPin(userId: string, dto: SetPinDto) {
    const transactionPinHash = await hashPassword(dto.pin);

    await this.prisma.user.update({
      where: { id: userId },
      data: { transactionPinHash },
    });

    return { hasTransactionPin: true };
  }

  // lets the Change PIN screen confirm the current PIN before letting the
  // user pick a new one, without actually spending anything
  async verifyPin(userId: string, dto: VerifyPinDto) {
    const user = await this.prisma.user.findUniqueOrThrow({
      where: { id: userId },
      select: { transactionPinHash: true },
    });

    if (!user.transactionPinHash) {
      throw new UnauthorizedException('No transaction PIN is set yet');
    }

    const isValid = await comparePassword(dto.pin, user.transactionPinHash);
    if (!isValid) {
      throw new UnauthorizedException('Incorrect PIN');
    }

    return { valid: true };
  }

  async changePassword(userId: string, dto: ChangePasswordDto) {
    const user = await this.prisma.user.findUniqueOrThrow({
      where: { id: userId },
      select: { passwordHash: true },
    });

    const isValid = await comparePassword(
      dto.currentPassword,
      user.passwordHash,
    );
    if (!isValid) {
      throw new UnauthorizedException('Current password is incorrect');
    }

    const passwordHash = await hashPassword(dto.newPassword);
    await this.prisma.user.update({
      where: { id: userId },
      data: { passwordHash },
    });

    // password just changed, so log every other device out
    await this.sessionService.deleteAllForUser(userId);
  }

  async listSessions(userId: string) {
    return this.sessionService.findAllForUser(userId);
  }

  async revokeSession(userId: string, sessionId: string) {
    await this.sessionService.deleteOneForUser(userId, sessionId);
  }

  async logoutAllDevices(userId: string) {
    await this.sessionService.deleteAllForUser(userId);
  }

  async getNotificationPreferences(userId: string) {
    return this.prisma.user.findUniqueOrThrow({
      where: { id: userId },
      select: {
        notifyGeneral: true,
        notifySmsAlerts: true,
        notifyCardTransactions: true,
        notifyTransfers: true,
        notifyOthers: true,
      },
    });
  }

  async updateNotificationPreferences(
    userId: string,
    dto: UpdateNotificationPreferencesDto,
  ) {
    return this.prisma.user.update({
      where: { id: userId },
      data: dto,
      select: {
        notifyGeneral: true,
        notifySmsAlerts: true,
        notifyCardTransactions: true,
        notifyTransfers: true,
        notifyOthers: true,
      },
    });
  }

  async deleteAccount(userId: string, dto: DeleteAccountDto) {
    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: { passwordHash: true },
    });
    if (!user) {
      throw new NotFoundException('Account not found');
    }

    const isValid = await comparePassword(dto.password, user.passwordHash);
    if (!isValid) {
      throw new UnauthorizedException('Password is incorrect');
    }

    // wallets, sessions, beneficiaries, transactions, merchants, voice
    // profile, and support messages all cascade from this delete
    await this.prisma.user.delete({ where: { id: userId } });
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
