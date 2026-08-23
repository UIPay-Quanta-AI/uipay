import {
  ConflictException,
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
    // there's no admin approval flow yet, so any merchant application (approved
    // or not) can register a tag for now
    const merchant = await this.findMerchantOrThrow(userId);

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

  private async findMerchantOrThrow(userId: string) {
    const merchant = await this.prisma.merchant.findFirst({
      where: { userId },
    });
    if (!merchant) {
      throw new NotFoundException('No merchant application found');
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
