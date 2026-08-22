import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateBeneficiaryDto } from './beneficiaries.dto';

@Injectable()
export class BeneficiariesService {
  constructor(private readonly prisma: PrismaService) {}

  async create(userId: string, dto: CreateBeneficiaryDto) {
    return this.prisma.beneficiary.create({
      data: { userId, ...dto },
    });
  }

  async findAll(userId: string) {
    return this.prisma.beneficiary.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
    });
  }

  async remove(userId: string, id: string) {
    // we dey check userId too, so nobody fit delete another person beneficiary
    // just by guessing the id
    const beneficiary = await this.prisma.beneficiary.findFirst({
      where: { id, userId },
    });

    if (!beneficiary) {
      throw new NotFoundException('Beneficiary not found');
    }

    await this.prisma.beneficiary.delete({ where: { id } });
  }
}
