import { ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { UpsertFinancialProfileDto } from './quanta-integration.dto';

const DEFAULT_PROFILE = {
  monthlyIncome: '0.00',
  incomeFrequency: 'monthly',
  employmentType: 'salaried',
  fixedExpenses: '0.00',
  variableExpenses: '0.00',
  savingsTarget: '0.00',
  currency: 'NGN',
};

// Field names here match quanta/app/domain/financial_profile/models.py
// exactly - Quanta validates this response directly with
// FinancialProfile.model_validate(), so it must not be wrapped in the
// usual { status, message, data } envelope.
function serialize(profile: {
  userId: string;
  monthlyIncome: { toString(): string };
  incomeFrequency: string;
  employmentType: string;
  fixedExpenses: { toString(): string };
  variableExpenses: { toString(): string };
  savingsTarget: { toString(): string };
  currency: string;
  createdAt: Date;
  updatedAt: Date;
}) {
  return {
    user_id: profile.userId,
    monthly_income: profile.monthlyIncome.toString(),
    income_frequency: profile.incomeFrequency,
    employment_type: profile.employmentType,
    fixed_expenses: profile.fixedExpenses.toString(),
    variable_expenses: profile.variableExpenses.toString(),
    savings_target: profile.savingsTarget.toString(),
    currency: profile.currency,
    created_at: profile.createdAt.toISOString(),
    updated_at: profile.updatedAt.toISOString(),
  };
}

@Injectable()
export class FinancialProfileService {
  constructor(private readonly prisma: PrismaService) {}

  async getProfile(userId: string) {
    const profile = await this.prisma.financialProfile.findUnique({
      where: { userId },
    });

    if (!profile) {
      throw new NotFoundException('Financial profile not found');
    }

    return serialize(profile);
  }

  // Quanta calls this once, the first time it needs a profile that doesn't
  // exist yet (get-or-initialize pattern in RealUIPayClient.get_financial_profile).
  // It always sends a full default body, so we just persist whatever it sends,
  // falling back to the same defaults it uses in case a field is missing.
  async createProfile(userId: string, dto: UpsertFinancialProfileDto) {
    try {
      const profile = await this.prisma.financialProfile.create({
        data: {
          userId,
          monthlyIncome: dto.monthly_income ?? DEFAULT_PROFILE.monthlyIncome,
          incomeFrequency: dto.income_frequency ?? DEFAULT_PROFILE.incomeFrequency,
          employmentType: dto.employment_type ?? DEFAULT_PROFILE.employmentType,
          fixedExpenses: dto.fixed_expenses ?? DEFAULT_PROFILE.fixedExpenses,
          variableExpenses: dto.variable_expenses ?? DEFAULT_PROFILE.variableExpenses,
          savingsTarget: dto.savings_target ?? DEFAULT_PROFILE.savingsTarget,
          currency: dto.currency ?? DEFAULT_PROFILE.currency,
        },
      });

      return serialize(profile);
    } catch (error) {
      // P2002 = unique constraint violation on userId - another request
      // already created this profile (the race RealUIPayClient's docstring
      // warns about). It falls back to a GET in that case, so a 409 here
      // is the correct, expected signal.
      if ((error as { code?: string }).code === 'P2002') {
        throw new ConflictException('Financial profile already exists');
      }
      throw error;
    }
  }

  async updateProfile(userId: string, dto: UpsertFinancialProfileDto) {
    const existing = await this.prisma.financialProfile.findUnique({
      where: { userId },
    });

    if (!existing) {
      throw new NotFoundException('Financial profile not found');
    }

    const profile = await this.prisma.financialProfile.update({
      where: { userId },
      data: {
        ...(dto.monthly_income !== undefined && { monthlyIncome: dto.monthly_income }),
        ...(dto.income_frequency !== undefined && { incomeFrequency: dto.income_frequency }),
        ...(dto.employment_type !== undefined && { employmentType: dto.employment_type }),
        ...(dto.fixed_expenses !== undefined && { fixedExpenses: dto.fixed_expenses }),
        ...(dto.variable_expenses !== undefined && { variableExpenses: dto.variable_expenses }),
        ...(dto.savings_target !== undefined && { savingsTarget: dto.savings_target }),
        ...(dto.currency !== undefined && { currency: dto.currency }),
      },
    });

    return serialize(profile);
  }
}
