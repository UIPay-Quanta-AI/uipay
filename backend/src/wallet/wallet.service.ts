import {
  BadRequestException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { createHash, randomUUID } from 'crypto';
import { PrismaService } from '../prisma/prisma.service';
import { TransferDto } from './wallet.dto';

// every new wallet enters with this fake alert, no real naira dey move here o
const STARTING_BALANCE = 50_000;
const TRANSFER_METHOD = 'wallet_transfer';

@Injectable()
export class WalletService {
  constructor(private readonly prisma: PrismaService) {}

  async createWallet(userId: string) {
    return this.prisma.wallet.create({
      data: { userId, balance: STARTING_BALANCE },
    });
  }

  async getBalance(userId: string) {
    const wallet = await this.findWalletOrThrow(userId);

    return { balance: wallet.balance, currency: wallet.currency };
  }

  async getAccountNumber(userId: string) {
    const wallet = await this.findWalletOrThrow(userId);

    return { accountNumber: this.fakeAccountNumber(wallet.id) };
  }

  async getHistory(userId: string) {
    return this.prisma.transaction.findMany({
      where: { OR: [{ senderId: userId }, { recipientId: userId }] },
      orderBy: { createdAt: 'desc' },
    });
  }

  async transfer(senderId: string, dto: TransferDto) {
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

      // this is the spot a real BaaS call (Anchor, Paystack etc) would sit once we
      // hook one up. for now we just debit one row and credit the other in the same
      // db transaction, no money dey enter or leave the system for real
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
          method: TRANSFER_METHOD,
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

  private fakeAccountNumber(walletId: string): string {
    // not a real NUBAN, just something stable-looking until BaaS gives us a real one
    const hash = createHash('sha256').update(walletId).digest('hex');
    return BigInt(`0x${hash.slice(0, 12)}`)
      .toString()
      .slice(0, 10)
      .padStart(10, '0');
  }
}
