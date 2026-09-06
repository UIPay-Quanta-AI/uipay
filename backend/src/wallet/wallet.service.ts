import {
  BadRequestException,
  Injectable,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { randomInt, randomUUID } from 'crypto';
import { comparePassword } from '../common/crypto/password';
import { PrismaService } from '../prisma/prisma.service';

// every new wallet starts with this fake balance, no real money is involved
const STARTING_BALANCE = 50_000;
const TRANSFER_METHOD = 'wallet_transfer';

@Injectable()
export class WalletService {
  constructor(private readonly prisma: PrismaService) {}

  async createWallet(userId: string) {
    const accountNumber = await this.generateUniqueAccountNumber();

    return this.prisma.wallet.create({
      data: { userId, balance: STARTING_BALANCE, accountNumber },
    });
  }

  async getBalance(userId: string) {
    const wallet = await this.findWalletOrThrow(userId);

    return { balance: wallet.balance, currency: wallet.currency };
  }

  async getAccountNumber(userId: string) {
    const wallet = await this.findWalletOrThrow(userId);

    return { accountNumber: wallet.accountNumber };
  }

  // lets a sender see who they're paying (name) before confirming, without
  // exposing anything beyond that name + the account number they already typed
  async resolveAccountNumber(accountNumber: string, currentUserId: string) {
    const wallet = await this.prisma.wallet.findUnique({
      where: { accountNumber },
      include: {
        user: { select: { id: true, firstName: true, lastName: true } },
      },
    });

    if (!wallet) {
      throw new NotFoundException('No UIPay account found with that number');
    }

    if (wallet.user.id === currentUserId) {
      throw new BadRequestException('you cannot send money to yourself');
    }

    return {
      userId: wallet.user.id,
      accountName: `${wallet.user.firstName} ${wallet.user.lastName}`,
    };
  }

  // distinct people this user has actually sent money to before - different
  // from the saved Beneficiary list, which is added explicitly
  async getRecentRecipients(userId: string) {
    const transactions = await this.prisma.transaction.findMany({
      where: { senderId: userId },
      distinct: ['recipientId'],
      orderBy: { createdAt: 'desc' },
      take: 10,
      include: {
        recipient: {
          select: {
            id: true,
            firstName: true,
            lastName: true,
            wallets: { select: { accountNumber: true }, take: 1 },
          },
        },
      },
    });

    return transactions.map((tx) => ({
      userId: tx.recipient.id,
      accountName: `${tx.recipient.firstName} ${tx.recipient.lastName}`,
      accountNumber: tx.recipient.wallets[0]?.accountNumber ?? null,
    }));
  }

  async getHistory(userId: string) {
    return this.prisma.transaction.findMany({
      where: { OR: [{ senderId: userId }, { recipientId: userId }] },
      orderBy: { createdAt: 'desc' },
    });
  }

  // NFC/QR merchant payments call transfer() directly with their own DTOs
  // that have no PIN concept, so PIN verification lives here as its own
  // step instead of inside transfer() - only the user-facing wallet
  // transfer endpoint calls it first.
  async verifyTransactionPin(userId: string, pin: string) {
    const user = await this.prisma.user.findUniqueOrThrow({
      where: { id: userId },
      select: { transactionPinHash: true },
    });

    if (!user.transactionPinHash) {
      throw new UnauthorizedException(
        'Set a transaction PIN before sending money',
      );
    }

    const isValidPin = await comparePassword(pin, user.transactionPinHash);
    if (!isValidPin) {
      throw new UnauthorizedException('Incorrect PIN');
    }
  }

  // takes just the fields movement actually needs - NFC/QR pass their own
  // pin-less objects here, so this can't require TransferDto's pin field
  async transfer(
    senderId: string,
    dto: { recipientId: string; amount: number },
    method = TRANSFER_METHOD,
  ) {
    if (senderId === dto.recipientId) {
      throw new BadRequestException('you cannot send money to yourself');
    }

    return this.prisma.$transaction(async (tx) => {
      const senderWallet = await tx.wallet.findFirst({
        where: { userId: senderId },
      });
      if (!senderWallet) {
        throw new NotFoundException('Sender wallet not found');
      }

      if (Number(senderWallet.balance) < dto.amount) {
        throw new BadRequestException('Insufficient balance');
      }

      const recipientWallet = await tx.wallet.findFirst({
        where: { userId: dto.recipientId },
      });
      if (!recipientWallet) {
        throw new NotFoundException('Recipient wallet not found');
      }

      // this is where a real BaaS call (Anchor, Paystack, etc) will go once we
      // integrate one. for now we just debit one row and credit the other,
      // no real money moves
      await tx.wallet.update({
        where: { id: senderWallet.id },
        data: { balance: { decrement: dto.amount } },
      });

      await tx.wallet.update({
        where: { id: recipientWallet.id },
        data: { balance: { increment: dto.amount } },
      });

      return tx.transaction.create({
        data: {
          senderId,
          recipientId: dto.recipientId,
          amount: dto.amount,
          method,
          reference: randomUUID(),
          status: 'success',
        },
      });
    });
  }

  private async findWalletOrThrow(userId: string) {
    const wallet = await this.prisma.wallet.findFirst({ where: { userId } });
    if (!wallet) {
      throw new NotFoundException('Wallet not found');
    }
    return wallet;
  }

  private async generateUniqueAccountNumber(): Promise<string> {
    // not a real NUBAN, just a stable, unique-looking number until a real
    // BaaS assigns one
    for (;;) {
      const candidate = randomInt(1_000_000_000, 10_000_000_000).toString();
      const existing = await this.prisma.wallet.findUnique({
        where: { accountNumber: candidate },
      });
      if (!existing) return candidate;
    }
  }
}
