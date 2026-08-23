import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { MerchantApplicationStatus, TransactionPeriod } from './admin.dto';

const DAY_MS = 24 * 60 * 60 * 1000;

@Injectable()
export class AdminService {
  constructor(private readonly prisma: PrismaService) {}

  async listUsers() {
    // never send back passwordHash, so select only the fields an admin needs
    return this.prisma.user.findMany({
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        middleName: true,
        phoneNumber: true,
        role: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  async listMerchants(status?: MerchantApplicationStatus) {
    return this.prisma.merchant.findMany({
      where: status ? { status } : undefined,
      include: {
        user: {
          select: { email: true, firstName: true, lastName: true },
        },
      },
      orderBy: { createdAt: 'desc' },
    });
  }

  async approveMerchant(id: string) {
    return this.setMerchantStatus(id, MerchantApplicationStatus.APPROVED);
  }

  async rejectMerchant(id: string) {
    return this.setMerchantStatus(id, MerchantApplicationStatus.REJECTED);
  }

  async getRevenue() {
    const transactions = await this.prisma.transaction.findMany({
      where: { status: 'success' },
    });

    const totalVolume = transactions.reduce(
      (sum, transaction) => sum + Number(transaction.amount),
      0,
    );

    const byMethod: Record<string, number> = {};
    for (const transaction of transactions) {
      byMethod[transaction.method] =
        (byMethod[transaction.method] ?? 0) + Number(transaction.amount);
    }

    // there's no transaction fee built in yet, so this is just total money
    // moved through the app, not real platform revenue
    return { totalVolume, byMethod };
  }

  async getTransactions(period: TransactionPeriod = TransactionPeriod.DAILY) {
    const since = this.periodStart(period);

    const transactions = await this.prisma.transaction.findMany({
      where: { createdAt: { gte: since } },
      orderBy: { createdAt: 'desc' },
    });

    const totalAmount = transactions.reduce(
      (sum, transaction) => sum + Number(transaction.amount),
      0,
    );

    return {
      period,
      since,
      count: transactions.length,
      totalAmount,
      transactions,
    };
  }

  async getNfcQrCount() {
    const [tagsRegistered, nfcPayments, qrPayments] = await Promise.all([
      this.prisma.nfcTag.count(),
      this.prisma.transaction.count({ where: { method: 'nfc' } }),
      this.prisma.transaction.count({ where: { method: 'qr' } }),
    ]);

    return {
      nfc: { tagsRegistered, payments: nfcPayments },
      qr: { payments: qrPayments },
    };
  }

  private async setMerchantStatus(
    id: string,
    status: MerchantApplicationStatus,
  ) {
    const merchant = await this.prisma.merchant.findUnique({ where: { id } });
    if (!merchant) {
      throw new NotFoundException('Merchant application not found');
    }

    return this.prisma.merchant.update({ where: { id }, data: { status } });
  }

  private periodStart(period: TransactionPeriod): Date {
    const now = Date.now();

    switch (period) {
      case TransactionPeriod.WEEKLY:
        return new Date(now - 7 * DAY_MS);
      case TransactionPeriod.MONTHLY:
        return new Date(now - 30 * DAY_MS);
      case TransactionPeriod.DAILY:
      default:
        return new Date(now - DAY_MS);
    }
  }
}
