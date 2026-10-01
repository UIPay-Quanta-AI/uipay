import { Injectable, NotFoundException } from '@nestjs/common';
import { Prisma } from '../../generated/prisma/client';
import { PrismaService } from '../prisma/prisma.service';
import { SaveBudgetDto } from './quanta-integration.dto';

// Field names match quanta/app/domain/budget/models.py exactly.
function serialize(budget: {
  id: string;
  userId: string;
  startDate: Date;
  endDate: Date;
  currency: string;
  version: number;
  status: string;
  incomePlan: unknown;
  allocations: unknown;
  goalAllocations: unknown;
  totalAllocatedExpenses: { toString(): string };
  totalAllocatedGoals: { toString(): string };
  totalUnallocatedIncome: { toString(): string };
  previousVersionId: string | null;
  updateReason: string;
  createdAt: Date;
  updatedAt: Date;
}) {
  return {
    id: budget.id,
    user_id: budget.userId,
    start_date: budget.startDate.toISOString().slice(0, 10),
    end_date: budget.endDate.toISOString().slice(0, 10),
    currency: budget.currency,
    version: budget.version,
    status: budget.status,
    income_plan: budget.incomePlan,
    allocations: budget.allocations,
    goal_allocations: budget.goalAllocations,
    total_allocated_expenses: budget.totalAllocatedExpenses.toString(),
    total_allocated_goals: budget.totalAllocatedGoals.toString(),
    total_unallocated_income: budget.totalUnallocatedIncome.toString(),
    previous_version_id: budget.previousVersionId,
    update_reason: budget.updateReason,
    created_at: budget.createdAt.toISOString(),
    updated_at: budget.updatedAt.toISOString(),
  };
}

@Injectable()
export class BudgetsService {
  constructor(private readonly prisma: PrismaService) {}

  // Versioned-budget pattern (see quanta/docs/BUDGET.md): saving never
  // mutates a row. It supersedes whatever was "active" and inserts a new
  // row with version+1, keeping the full history queryable.
  async saveBudget(userId: string, dto: SaveBudgetDto) {
    const current = await this.prisma.budget.findFirst({
      where: { userId, status: 'active' },
      orderBy: { version: 'desc' },
    });

    if (current) {
      await this.prisma.budget.update({
        where: { id: current.id },
        data: { status: 'superseded' },
      });
    }

    const budget = await this.prisma.budget.create({
      data: {
        userId,
        startDate: new Date(dto.start_date),
        endDate: new Date(dto.end_date),
        currency: dto.currency ?? 'NGN',
        version: (current?.version ?? 0) + 1,
        status: 'active',
        incomePlan: (dto.income_plan ?? {}) as Prisma.InputJsonValue,
        allocations: (dto.allocations ?? []) as Prisma.InputJsonValue,
        goalAllocations: (dto.goal_allocations ?? []) as Prisma.InputJsonValue,
        totalAllocatedExpenses: dto.total_allocated_expenses ?? '0.00',
        totalAllocatedGoals: dto.total_allocated_goals ?? '0.00',
        totalUnallocatedIncome: dto.total_unallocated_income ?? '0.00',
        previousVersionId: current?.id ?? null,
        updateReason: dto.update_reason ?? 'initial_generation',
      },
    });

    return serialize(budget);
  }

  async getCurrentBudget(userId: string) {
    const budget = await this.prisma.budget.findFirst({
      where: { userId, status: 'active' },
      orderBy: { version: 'desc' },
    });

    if (!budget) {
      throw new NotFoundException('No current budget');
    }

    return serialize(budget);
  }

  async getBudgetHistory(userId: string) {
    const budgets = await this.prisma.budget.findMany({
      where: { userId },
      orderBy: { version: 'desc' },
    });

    return budgets.map(serialize);
  }
}
