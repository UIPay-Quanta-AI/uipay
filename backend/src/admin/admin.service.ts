import { Injectable, NotFoundException } from '@nestjs/common';
import { SessionService } from '../auth/session/session.service';
import { PrismaService } from '../prisma/prisma.service';
import { QrService } from '../qr/qr.service';
import { WalletService } from '../wallet/wallet.service';
import {
  MerchantApplicationStatus,
  TransactionFlagReason,
  TransactionPeriod,
} from './admin.dto';

const DAY_MS = 24 * 60 * 60 * 1000;
const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

@Injectable()
export class AdminService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly sessionService: SessionService,
    private readonly walletService: WalletService,
    private readonly qrService: QrService,
  ) {}

  async listUsers() {
    const users = await this.prisma.user.findMany({
      // never send back passwordHash/transactionPinHash, so select only
      // the fields an admin needs
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        middleName: true,
        phoneNumber: true,
        role: true,
        status: true,
        identityVerifiedAt: true,
        createdAt: true,
      },
      orderBy: { createdAt: 'desc' },
    });

    // identityVerifiedAt is the only signal we actually have for a KYC
    // "tier" today - verified users are Tier 2, everyone else is Tier 1.
    // There is no numeric tier stored anywhere yet.
    return users.map((user) => ({
      ...user,
      tier: user.identityVerifiedAt ? 2 : 1,
    }));
  }

  async getUserDetail(id: string) {
    const user = await this.prisma.user.findUnique({
      where: { id },
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        middleName: true,
        phoneNumber: true,
        dob: true,
        role: true,
        status: true,
        identityVerifiedAt: true,
        createdAt: true,
      },
    });
    if (!user) {
      throw new NotFoundException('User not found');
    }

    const [balance, transactionCount] = await Promise.all([
      this.walletService.getBalance(id).catch(() => null),
      this.prisma.transaction.count({
        where: { OR: [{ senderId: id }, { recipientId: id }] },
      }),
    ]);

    return {
      ...user,
      tier: user.identityVerifiedAt ? 2 : 1,
      balance: balance?.balance ?? null,
      currency: balance?.currency ?? null,
      totalTransactions: transactionCount,
    };
  }

  async getUserActivity(id: string) {
    const user = await this.prisma.user.findUnique({ where: { id } });
    if (!user) {
      throw new NotFoundException('User not found');
    }

    return this.walletService.getHistory(id);
  }

  async suspendUser(id: string) {
    const user = await this.setUserStatus(id, 'suspended');
    // block any refresh token this user is currently holding immediately -
    // their current access token still works until it naturally expires
    // (JwtAuthGuard doesn't hit the DB), same tradeoff already accepted
    // elsewhere in this codebase (e.g. forgot-password)
    await this.sessionService.deleteAllForUser(id);
    return user;
  }

  async reactivateUser(id: string) {
    return this.setUserStatus(id, 'active');
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

  async getMerchantDetail(id: string) {
    const merchant = await this.prisma.merchant.findUnique({
      where: { id },
      include: {
        user: {
          select: { email: true, firstName: true, lastName: true },
        },
      },
    });
    if (!merchant) {
      throw new NotFoundException('Merchant application not found');
    }
    return merchant;
  }

  async approveMerchant(id: string) {
    return this.setMerchantStatus(id, MerchantApplicationStatus.APPROVED);
  }

  async rejectMerchant(id: string) {
    return this.setMerchantStatus(id, MerchantApplicationStatus.REJECTED);
  }

  async getRevenue(period: TransactionPeriod = TransactionPeriod.DAILY) {
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
    return {
      totalVolume,
      transactionCount: transactions.length,
      byMethod,
      series: this.buildRevenueSeries(transactions, period),
    };
  }

  async getTransactions(period: TransactionPeriod = TransactionPeriod.DAILY) {
    const since = this.periodStart(period);

    const transactions = await this.prisma.transaction.findMany({
      where: { createdAt: { gte: since } },
      orderBy: { createdAt: 'desc' },
      include: {
        sender: { select: { firstName: true, lastName: true } },
        recipient: { select: { firstName: true, lastName: true } },
      },
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
      transactions: transactions.map(({ sender, recipient, ...tx }) => ({
        ...tx,
        senderName: `${sender.firstName} ${sender.lastName}`,
        recipientName: `${recipient.firstName} ${recipient.lastName}`,
      })),
    };
  }

  async getTransactionDetail(id: string) {
    const transaction = await this.prisma.transaction.findUnique({
      where: { id },
      include: {
        sender: { select: { firstName: true, lastName: true } },
        recipient: { select: { firstName: true, lastName: true } },
      },
    });
    if (!transaction) {
      throw new NotFoundException('Transaction not found');
    }

    const { sender, recipient, ...tx } = transaction;
    return {
      ...tx,
      senderName: `${sender.firstName} ${sender.lastName}`,
      recipientName: `${recipient.firstName} ${recipient.lastName}`,
    };
  }

  async flagTransaction(id: string, reason: TransactionFlagReason) {
    const transaction = await this.prisma.transaction.findUnique({
      where: { id },
    });
    if (!transaction) {
      throw new NotFoundException('Transaction not found');
    }

    return this.prisma.transaction.update({
      where: { id },
      data: { flagged: true, flagReason: reason },
    });
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

  // lets an admin hand a customer a scannable code that pays a specific
  // user directly - useful for a recipient who isn't a merchant at all
  async generateQrForUser(recipientId: string, amount: number) {
    return this.qrService.generateForAdmin(recipientId, amount);
  }

  private async setUserStatus(id: string, status: 'active' | 'suspended') {
    const user = await this.prisma.user.findUnique({ where: { id } });
    if (!user) {
      throw new NotFoundException('User not found');
    }

    // never send back passwordHash/transactionPinHash
    return this.prisma.user.update({
      where: { id },
      data: { status },
      select: {
        id: true,
        email: true,
        firstName: true,
        lastName: true,
        middleName: true,
        phoneNumber: true,
        role: true,
        status: true,
        identityVerifiedAt: true,
        createdAt: true,
      },
    });
  }

  private async setMerchantStatus(
    id: string,
    status: MerchantApplicationStatus,
  ) {
    const merchant = await this.prisma.merchant.findUnique({ where: { id } });
    if (!merchant) {
      throw new NotFoundException('Merchant application not found');
    }

    // include the same `user` relation as list/detail so the frontend can
    // keep rendering the same shape after an approve/reject action
    return this.prisma.merchant.update({
      where: { id },
      data: { status },
      include: {
        user: { select: { email: true, firstName: true, lastName: true } },
      },
    });
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

  // "Daily" -> one bar per day for the current week (Mon..Sun so far).
  // "Weekly" -> one bar per week for the last 8 weeks.
  // "Monthly" -> one bar per month for the last 6 months.
  // This is a lightweight admin analytics view, not a financial ledger, so
  // buckets are computed in JS rather than a real SQL GROUP BY.
  private buildRevenueSeries(
    transactions: { amount: unknown; createdAt: Date }[],
    period: TransactionPeriod,
  ): { label: string; amount: number }[] {
    const now = new Date();

    if (period === TransactionPeriod.WEEKLY) {
      const buckets = new Array<number>(8).fill(0);
      const labels: string[] = [];
      for (let i = 7; i >= 0; i--) {
        const start = new Date(now.getTime() - i * 7 * DAY_MS);
        labels.push(`${start.getMonth() + 1}/${start.getDate()}`);
      }
      for (const tx of transactions) {
        const weeksAgo = Math.floor(
          (now.getTime() - tx.createdAt.getTime()) / (7 * DAY_MS),
        );
        const index = 7 - weeksAgo;
        if (index >= 0 && index < 8) {
          buckets[index] += Number(tx.amount);
        }
      }
      return labels.map((label, i) => ({ label, amount: buckets[i] }));
    }

    if (period === TransactionPeriod.MONTHLY) {
      const buckets = new Array<number>(6).fill(0);
      const labels: string[] = [];
      for (let i = 5; i >= 0; i--) {
        const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
        labels.push(d.toLocaleString('en-US', { month: 'short' }));
      }
      for (const tx of transactions) {
        const monthsAgo =
          (now.getFullYear() - tx.createdAt.getFullYear()) * 12 +
          (now.getMonth() - tx.createdAt.getMonth());
        const index = 5 - monthsAgo;
        if (index >= 0 && index < 6) {
          buckets[index] += Number(tx.amount);
        }
      }
      return labels.map((label, i) => ({ label, amount: buckets[i] }));
    }

    // DAILY: last 7 calendar days, oldest first
    const buckets = new Array<number>(7).fill(0);
    const labels: string[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now.getTime() - i * DAY_MS);
      labels.push(WEEKDAY_LABELS[d.getDay()]);
    }
    for (const tx of transactions) {
      const daysAgo = Math.floor(
        (now.getTime() - tx.createdAt.getTime()) / DAY_MS,
      );
      const index = 6 - daysAgo;
      if (index >= 0 && index < 7) {
        buckets[index] += Number(tx.amount);
      }
    }
    return labels.map((label, i) => ({ label, amount: buckets[i] }));
  }
}
