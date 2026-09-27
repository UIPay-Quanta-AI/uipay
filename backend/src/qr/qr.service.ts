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

// admin-issued codes pay a specific user directly, not a merchant
// application - kept in a separate redis key namespace so they can't
// collide with (or be confused for) merchant-issued codes
const ADMIN_QR_TTL_SECONDS = 15 * 60;

interface AdminDynamicQrPayload {
  recipientId: string;
  amount: number;
}

interface ResolvedQrCode {
  recipientUserId: string;
  displayName: string;
  category: string | null;
  type: QrCodeType;
  amount?: number;
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

    // field names kept as businessName/category for backward compatibility -
    // the frontend scan flow just displays these as "who you're paying" /
    // a subtitle, so an admin-issued code (real name, no category) fits the
    // same shape without any frontend change
    return {
      recipientId: resolved.recipientUserId,
      businessName: resolved.displayName,
      category: resolved.category,
      type: resolved.type,
      amount: resolved.amount,
    };
  }

  async pay(customerId: string, dto: PayWithQrDto) {
    await this.walletService.verifyTransactionPin(customerId, dto.pin);

    const resolved = await this.resolveQrCode(dto.qrCode);

    const amount = resolved.amount ?? dto.amount;
    if (!amount) {
      throw new BadRequestException('Amount is required for this QR code');
    }

    const transaction = await this.walletService.transfer(
      customerId,
      { recipientId: resolved.recipientUserId, amount },
      QR_PAYMENT_METHOD,
    );

    // dynamic codes can only be used once, so remove it once it's been paid
    if (resolved.type === QrCodeType.DYNAMIC) {
      await this.redis.client.del(`qr:dynamic:${dto.qrCode}`);
      await this.redis.client.del(`qr:admin-dynamic:${dto.qrCode}`);
    }

    return transaction;
  }

  // admin-only: a dynamic code that pays a specific user directly, e.g. so
  // a customer can scan and pay without that user needing a merchant
  // application at all
  async generateForAdmin(recipientId: string, amount: number) {
    const recipient = await this.prisma.user.findUnique({
      where: { id: recipientId },
    });
    if (!recipient) {
      throw new NotFoundException('Recipient user was not found');
    }

    const qrCode = randomUUID();
    const payload: AdminDynamicQrPayload = { recipientId, amount };

    await this.redis.client.set(
      `qr:admin-dynamic:${qrCode}`,
      JSON.stringify(payload),
      'EX',
      ADMIN_QR_TTL_SECONDS,
    );

    return {
      qrCode,
      type: QrCodeType.DYNAMIC,
      amount,
      expiresIn: ADMIN_QR_TTL_SECONDS,
      recipientName: `${recipient.firstName} ${recipient.lastName}`,
    };
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

  private async resolveQrCode(qrCode: string): Promise<ResolvedQrCode> {
    const adminPayload = await this.redis.client.get(
      `qr:admin-dynamic:${qrCode}`,
    );
    if (adminPayload) {
      const { recipientId, amount }: AdminDynamicQrPayload =
        JSON.parse(adminPayload);

      const recipient = await this.prisma.user.findUnique({
        where: { id: recipientId },
      });
      if (!recipient) {
        throw new NotFoundException('Recipient for this QR code was not found');
      }

      return {
        recipientUserId: recipient.id,
        displayName: `${recipient.firstName} ${recipient.lastName}`,
        category: null,
        type: QrCodeType.DYNAMIC,
        amount,
      };
    }

    const dynamicPayload = await this.redis.client.get(`qr:dynamic:${qrCode}`);

    if (dynamicPayload) {
      const { merchantId, amount }: DynamicQrPayload =
        JSON.parse(dynamicPayload);

      const merchant = await this.prisma.merchant.findUnique({
        where: { id: merchantId },
      });
      if (!merchant) {
        throw new NotFoundException('Merchant for this QR code was not found');
      }

      return {
        recipientUserId: merchant.userId,
        displayName: merchant.businessName,
        category: merchant.category,
        type: QrCodeType.DYNAMIC,
        amount,
      };
    }

    const merchant = await this.prisma.merchant.findFirst({
      where: { qrCodeUrl: qrCode },
    });
    if (!merchant) {
      throw new NotFoundException('QR code not found or expired');
    }

    return {
      recipientUserId: merchant.userId,
      displayName: merchant.businessName,
      category: merchant.category,
      type: QrCodeType.STATIC,
      amount: undefined,
    };
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
