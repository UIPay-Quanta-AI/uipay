import {
  ConflictException,
  ForbiddenException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { WalletService } from '../wallet/wallet.service';
import { PayWithTagDto, RegisterTagDto } from './nfc.dto';

const NFC_PAYMENT_METHOD = 'nfc';

@Injectable()
export class NfcService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly walletService: WalletService,
  ) {}

  async register(userId: string, dto: RegisterTagDto) {
    // only an approved merchant can register a tag, otherwise anyone could
    // apply and start accepting payments before an admin reviews them
    const merchant = await this.findApprovedMerchantOrThrow(userId);

    const existingTag = await this.prisma.nfcTag.findUnique({
      where: { id: dto.tagId },
    });
    if (existingTag) {
      throw new ConflictException('This tag is already registered');
    }

    return this.prisma.nfcTag.create({
      data: { id: dto.tagId, merchantId: merchant.id },
    });
  }

  // only send back what the customer's app needs to show who they're paying,
  // nothing about the merchant's account or the person behind it
  async resolve(tagId: string) {
    const tag = await this.findActiveTagOrThrow(tagId);

    return {
      merchantId: tag.merchant.id,
      businessName: tag.merchant.businessName,
      category: tag.merchant.category,
    };
  }

  async pay(customerId: string, dto: PayWithTagDto) {
    const tag = await this.findActiveTagOrThrow(dto.tagId);

    return this.walletService.transfer(
      customerId,
      { recipientId: tag.merchant.userId, amount: dto.amount },
      NFC_PAYMENT_METHOD,
    );
  }

  private async findApprovedMerchantOrThrow(userId: string) {
    const merchant = await this.prisma.merchant.findFirst({
      where: { userId },
    });
    if (!merchant) {
      throw new NotFoundException('No merchant application found');
    }
    if (merchant.status !== 'approved') {
      throw new ForbiddenException('Merchant application is not approved yet');
    }
    return merchant;
  }

  private async findActiveTagOrThrow(tagId: string) {
    const tag = await this.prisma.nfcTag.findUnique({
      where: { id: tagId },
      include: { merchant: true },
    });

    if (!tag || !tag.active) {
      throw new NotFoundException('Tag not found or inactive');
    }

    return tag;
  }
}
