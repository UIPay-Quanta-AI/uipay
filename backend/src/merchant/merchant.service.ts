import {
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { WalletService } from '../wallet/wallet.service';
import { ApplyMerchantDto } from './merchant.dto';

@Injectable()
export class MerchantService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly walletService: WalletService,
  ) {}

  async apply(userId: string, dto: ApplyMerchantDto) {
    const existing = await this.prisma.merchant.findFirst({
      where: { userId },
    });
    if (existing) {
      throw new ConflictException('Merchant application already exists');
    }

    // qrCodeUrl no dey set here, na the QR/NFC module go fill am in later
    return this.prisma.merchant.create({
      data: {
        userId,
        applicantType: dto.applicantType,
        businessName: dto.businessName,
        category: dto.category,
      },
    });
  }

  async getProfile(userId: string) {
    return this.findMerchantOrThrow(userId);
  }

  async getTransactions(userId: string) {
    await this.findMerchantOrThrow(userId);

    return this.prisma.transaction.findMany({
      where: { OR: [{ senderId: userId }, { recipientId: userId }] },
      orderBy: { createdAt: 'desc' },
    });
  }

  async getBalance(userId: string) {
    await this.findMerchantOrThrow(userId);

    return this.walletService.getBalance(userId);
  }

  private async findMerchantOrThrow(userId: string) {
    const merchant = await this.prisma.merchant.findFirst({
      where: { userId },
    });
    if (!merchant) {
      throw new NotFoundException('No merchant application found');
    }
    return merchant;
  }
}
