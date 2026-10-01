import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

// Our internal Transaction.status values don't match the vocabulary
// transaction_intelligence/rules.py:map_status() understands (COMPLETED,
// SETTLED, PENDING, FAILED, REVERSED, CANCELLED) - anything else becomes
// UNKNOWN there and gets silently excluded from analysis, so it has to be
// translated explicitly rather than passed through.
const STATUS_MAP: Record<string, string> = {
  success: 'COMPLETED',
  pending: 'PENDING',
  failed: 'FAILED',
};

@Injectable()
export class TransactionsService {
  constructor(private readonly prisma: PrismaService) {}

  async getTransactions(userId: string, startDate?: string, endDate?: string) {
    const createdAt: { gte?: Date; lte?: Date } = {};
    if (startDate) createdAt.gte = new Date(`${startDate}T00:00:00.000Z`);
    if (endDate) createdAt.lte = new Date(`${endDate}T23:59:59.999Z`);

    const transactions = await this.prisma.transaction.findMany({
      where: {
        OR: [{ senderId: userId }, { recipientId: userId }],
        ...(startDate || endDate ? { createdAt } : {}),
      },
      include: {
        sender: { select: { firstName: true, lastName: true } },
        recipient: { select: { firstName: true, lastName: true } },
      },
      orderBy: { createdAt: 'desc' },
    });

    // Every row is a wallet-to-wallet movement between two UI Pay users -
    // it's always a TRANSFER, never INCOME/EXPENSE, so budget math doesn't
    // mistake moving money to a friend for real spending.
    return transactions.map((tx) => {
      const isOutbound = tx.senderId === userId;
      const counterparty = isOutbound ? tx.recipient : tx.sender;

      return {
        id: tx.id,
        reference: tx.reference,
        amount: tx.amount.toString(),
        currency: 'NGN',
        direction: isOutbound ? 'OUTBOUND' : 'INBOUND',
        classification: 'TRANSFER',
        category: 'TRANSFER',
        counterparty_type: 'BENEFICIARY',
        beneficiary_name: `${counterparty.firstName} ${counterparty.lastName}`,
        status: STATUS_MAP[tx.status] ?? 'UNKNOWN',
        description: `Wallet transfer via ${tx.method}`,
        date: tx.createdAt.toISOString().slice(0, 10),
      };
    });
  }

  // Quanta gracefully degrades when this is unavailable (see
  // quanta/docs/BUDGET.md) - an honest { data_available: false } is a
  // legitimate response, not a stub, until real trend aggregation is built.
  getTransactionContext() {
    return { data_available: false };
  }
}
