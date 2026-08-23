/* eslint-disable @typescript-eslint/no-unsafe-assignment */
import {
  BadRequestException,
  ForbiddenException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { createHash, randomUUID } from 'crypto';
import { PrismaService } from '../prisma/prisma.service';
import { RedisService } from '../redis/redis.service';
import { WalletService } from '../wallet/wallet.service';
import { GenerateQrDto, PayWithQrDto, QrCodeType } from './qr.dto';

const QR_PAYMENT_METHOD = 'qr';
// dynamic codes are meant for a single purchase, so they only last 15 minutes
const DYNAMIC_QR_TTL_SECONDS = 15 * 60;

interface DynamicQrPayload {
  merchantId: string;
  amount: number;
}

@Injectable()
export class QrService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly redis: RedisService,
    private readonly walletService: WalletService,
  ) {}

  async generate(userId: string, dto: GenerateQrDto) {
    // only an approved merchant can generate a code, otherwise anyone could
    // apply and start accepting payments before an admin reviews them
    const merchant = await this.findApprovedMerchantOrThrow(userId);

    if (dto.type === QrCodeType.DYNAMIC) {
      return this.generateDynamicCode(merchant.id, dto.amount!);
    }

    return this.generateStaticCode(merchant.id, merchant.qrCodeUrl);
  }

  async validate(qrCode: string) {
    const resolved = await this.resolveQrCode(qrCode);

    return {
      merchantId: resolved.merchant.id,
      businessName: resolved.merchant.businessName,
      category: resolved.merchant.category,
      type: resolved.type,
      amount: resolved.amount,
    };
  }

  async pay(customerId: string, dto: PayWithQrDto) {
    const resolved = await this.resolveQrCode(dto.qrCode);

    const amount = resolved.amount ?? dto.amount;
    if (!amount) {
      throw new BadRequestException('Amount is required for this QR code');
    }

    const transaction = await this.walletService.transfer(
      customerId,
      { recipientId: resolved.merchant.userId, amount },
      QR_PAYMENT_METHOD,
    );

    // dynamic codes can only be used once, so remove it once it's been paid
    if (resolved.type === QrCodeType.DYNAMIC) {
      await this.redis.client.del(`qr:dynamic:${dto.qrCode}`);
    }

    return transaction;
  }

  private async generateDynamicCode(merchantId: string, amount: number) {
    const qrCode = randomUUID();
    const payload: DynamicQrPayload = { merchantId, amount };

    await this.redis.client.set(
      `qr:dynamic:${qrCode}`,
      JSON.stringify(payload),
      'EX',
      DYNAMIC_QR_TTL_SECONDS,
    );

    return {
      qrCode,
      type: QrCodeType.DYNAMIC,
      amount,
      expiresIn: DYNAMIC_QR_TTL_SECONDS,
    };
  }

  private async generateStaticCode(
    merchantId: string,
    existingCode: string | null,
  ) {
    // static codes don't expire, so we save one value on the merchant the
    // first time and just hand back the same one on every later request
    const qrCode = existingCode ?? this.staticQrCode(merchantId);

    if (!existingCode) {
      await this.prisma.merchant.update({
        where: { id: merchantId },
        data: { qrCodeUrl: qrCode },
      });
    }

    return { qrCode, type: QrCodeType.STATIC };
  }

  private async resolveQrCode(qrCode: string) {
    const dynamicPayload = await this.redis.client.get(
      `qr:dynamic:${qrCode}`,
    );

    if (dynamicPayload) {
      const { merchantId, amount }: DynamicQrPayload =
        JSON.parse(dynamicPayload);

      const merchant = await this.prisma.merchant.findUnique({
        where: { id: merchantId },
      });
      if (!merchant) {
        throw new NotFoundException(
          'Merchant for this QR code was not found',
        );
      }

      return { merchant, type: QrCodeType.DYNAMIC, amount };
    }

    const merchant = await this.prisma.merchant.findFirst({
      where: { qrCodeUrl: qrCode },
    });
    if (!merchant) {
      throw new NotFoundException('QR code not found or expired');
    }

    return { merchant, type: QrCodeType.STATIC, amount: undefined };
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

  private staticQrCode(merchantId: string): string {
    // just a stable id derived from the merchant, not a real signed QR payload
    return createHash('sha256').update(merchantId).digest('hex').slice(0, 24);
  }
}
