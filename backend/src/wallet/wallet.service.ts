import {
  BadRequestException,
  Injectable,
  Logger,
  NotFoundException,
  UnauthorizedException,
} from '@nestjs/common';
import { randomInt, randomUUID } from 'crypto';
import { comparePassword } from '../common/crypto/password';
import { PrismaService } from '../prisma/prisma.service';
import { PaystackService } from './paystack.service';

// every new wallet starts with this fake balance, no real money is involved
const STARTING_BALANCE = 50_000;
const TRANSFER_METHOD = 'wallet_transfer';
const KOBO_PER_NAIRA = 100;

@Injectable()
export class WalletService {
  private readonly logger = new Logger(WalletService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly paystackService: PaystackService,
  ) {}

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

  // Combines peer-to-peer transfers with successful wallet-funding events
  // into one feed. A funding has no counterpart user (the money comes from
  // a card via Paystack, not another UIPay account), so it's tagged with
  // type: 'funding' rather than forced into the sender/recipient shape -
  // the frontend uses that to render it with its own icon/label instead of
  // a person's initials.
  async getHistory(userId: string) {
    const [transactions, fundings] = await Promise.all([
      this.prisma.transaction.findMany({
        where: { OR: [{ senderId: userId }, { recipientId: userId }] },
        include: {
          sender: { select: { firstName: true, lastName: true } },
          recipient: { select: { firstName: true, lastName: true } },
        },
      }),
      this.prisma.walletFunding.findMany({
        where: { userId, status: 'success' },
      }),
    ]);

    // flatten to plain counterpart names so the frontend doesn't need to
    // know which side of sender/recipient it's looking at
    const transferItems = transactions.map(({ sender, recipient, ...tx }) => ({
      ...tx,
      type: 'transfer' as const,
      senderName: `${sender.firstName} ${sender.lastName}`,
      recipientName: `${recipient.firstName} ${recipient.lastName}`,
    }));

    const fundingItems = fundings.map((funding) => ({
      id: funding.id,
      type: 'funding' as const,
      senderId: null,
      recipientId: userId,
      senderName: 'Paystack',
      recipientName: 'You',
      amount: funding.amount,
      method: 'wallet_funding',
      reference: funding.reference,
      status: funding.status,
      createdAt: funding.createdAt,
      updatedAt: funding.updatedAt,
    }));

    return [...transferItems, ...fundingItems].sort(
      (a, b) => b.createdAt.getTime() - a.createdAt.getTime(),
    );
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

  // Step 1 of funding a wallet with real money: create a pending record and
  // ask Paystack for a checkout session. Nothing is credited yet - that only
  // happens once we get a confirmed "success" back (see creditIfPending).
  async initiateFunding(userId: string, email: string, amountNaira: number) {
    await this.findWalletOrThrow(userId);

    const reference = `uipay-fund-${randomUUID()}`;

    await this.prisma.walletFunding.create({
      data: {
        userId,
        reference,
        amount: amountNaira,
        status: 'pending',
      },
    });

    const result = await this.paystackService.initializeTransaction({
      email,
      amountKobo: Math.round(amountNaira * KOBO_PER_NAIRA),
      reference,
    });

    return {
      reference: result.reference,
      authorizationUrl: result.authorizationUrl,
      amount: amountNaira,
    };
  }

  // Called by the frontend right after Paystack's popup reports success, for
  // immediate feedback. Never trusts the client's word for it - re-verifies
  // with Paystack directly before crediting anything.
  async verifyFunding(userId: string, reference: string) {
    const funding = await this.prisma.walletFunding.findUnique({
      where: { reference },
    });
    if (!funding || funding.userId !== userId) {
      throw new NotFoundException('Funding attempt not found');
    }

    if (funding.status === 'success') {
      return { status: 'success', amount: funding.amount };
    }

    const verified = await this.paystackService.verifyTransaction(reference);
    const expectedKobo = Math.round(Number(funding.amount) * KOBO_PER_NAIRA);

    if (verified.status !== 'success' || verified.amountKobo !== expectedKobo) {
      if (funding.status === 'pending') {
        await this.prisma.walletFunding.update({
          where: { id: funding.id },
          data: { status: 'failed' },
        });
      }
      return { status: 'failed', amount: funding.amount };
    }

    const credited = await this.creditIfPending(funding.id);
    if (credited) {
      return { status: 'success', amount: funding.amount };
    }

    // We didn't win the credit race - most likely the webhook got here
    // first and already marked it success. Re-read the current row rather
    // than trusting the stale "pending" snapshot from the top of this call.
    const current = await this.prisma.walletFunding.findUniqueOrThrow({
      where: { id: funding.id },
    });
    return { status: current.status, amount: current.amount };
  }

  // The reliable path: Paystack calls this directly from their servers, so
  // it doesn't depend on the user's browser staying open. Signature is
  // verified by the caller (see WalletWebhookController) before this runs.
  async handlePaystackWebhookEvent(event: {
    event: string;
    data?: { reference?: string };
  }) {
    if (event.event !== 'charge.success' || !event.data?.reference) {
      return;
    }

    const reference = event.data.reference;
    const funding = await this.prisma.walletFunding.findUnique({
      where: { reference },
    });
    if (!funding || funding.status !== 'pending') {
      return;
    }

    // Re-verify with Paystack rather than trusting the webhook payload's
    // amount directly - the signature proves the request came from
    // Paystack, but a fresh verify call is the authoritative source for
    // exactly how much was actually paid.
    const verified = await this.paystackService.verifyTransaction(reference);
    const expectedKobo = Math.round(Number(funding.amount) * KOBO_PER_NAIRA);

    if (verified.status !== 'success' || verified.amountKobo !== expectedKobo) {
      this.logger.warn(
        `Webhook charge.success for ${reference} did not match a pending funding of the expected amount`,
      );
      return;
    }

    await this.creditIfPending(funding.id);
  }

  // Atomically claims a pending funding row and credits the wallet. Safe to
  // call from both the verify endpoint and the webhook - whichever gets here
  // first flips the status; the other sees claim.count === 0 and does
  // nothing, so the wallet is never credited twice for one funding.
  private async creditIfPending(fundingId: string): Promise<boolean> {
    return this.prisma.$transaction(async (tx) => {
      const claim = await tx.walletFunding.updateMany({
        where: { id: fundingId, status: 'pending' },
        data: { status: 'success' },
      });
      if (claim.count === 0) {
        return false;
      }

      const funding = await tx.walletFunding.findUniqueOrThrow({
        where: { id: fundingId },
      });
      const wallet = await tx.wallet.findFirst({
        where: { userId: funding.userId },
      });
      if (!wallet) {
        throw new NotFoundException('Wallet not found');
      }

      await tx.wallet.update({
        where: { id: wallet.id },
        data: { balance: { increment: funding.amount } },
      });

      return true;
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
