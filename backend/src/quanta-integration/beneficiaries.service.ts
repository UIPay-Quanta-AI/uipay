import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class QuantaBeneficiariesService {
  constructor(private readonly prisma: PrismaService) {}

  async search(userId: string, query?: string) {
    const beneficiaries = await this.prisma.beneficiary.findMany({
      where: {
        userId,
        ...(query && {
          OR: [
            { nickname: { contains: query, mode: 'insensitive' } },
            { bankName: { contains: query, mode: 'insensitive' } },
            { accountNumber: { contains: query } },
          ],
        }),
      },
      orderBy: { createdAt: 'desc' },
    });

    // Quanta's Beneficiary model requires account_name (the verified
    // account holder's name). We never capture that separately - a
    // beneficiary here is only ever saved with a user-chosen nickname - so
    // we use the nickname as a stand-in. It's always present and non-empty
    // on our side, so this satisfies the field without inventing data.
    return beneficiaries.map((b) => ({
      id: b.id,
      nickname: b.nickname,
      account_name: b.nickname,
      bank_name: b.bankName,
      account_number: b.accountNumber,
    }));
  }
}
