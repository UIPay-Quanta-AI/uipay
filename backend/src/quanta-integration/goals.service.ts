import { Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateGoalDto, UpdateGoalDto } from './quanta-integration.dto';

// Field names match quanta/app/domain/goals/models.py exactly. Quanta
// computes remaining_amount itself (target_amount - current_amount) - it's
// not a stored field, so we never send it.
function serialize(goal: {
  id: string;
  userId: string;
  name: string;
  targetAmount: { toString(): string };
  currentAmount: { toString(): string };
  targetDate: Date | null;
  currency: string;
  status: string;
  createdAt: Date;
  updatedAt: Date;
}) {
  return {
    id: goal.id,
    user_id: goal.userId,
    name: goal.name,
    target_amount: goal.targetAmount.toString(),
    current_amount: goal.currentAmount.toString(),
    target_date: goal.targetDate
      ? goal.targetDate.toISOString().slice(0, 10)
      : null,
    currency: goal.currency,
    status: goal.status,
    created_at: goal.createdAt.toISOString(),
    updated_at: goal.updatedAt.toISOString(),
  };
}

@Injectable()
export class GoalsService {
  constructor(private readonly prisma: PrismaService) {}

  async createGoal(userId: string, dto: CreateGoalDto) {
    const goal = await this.prisma.goal.create({
      data: {
        userId,
        name: dto.name,
        targetAmount: dto.target_amount,
        currentAmount: dto.current_amount ?? '0.00',
        targetDate: dto.target_date ? new Date(dto.target_date) : undefined,
        currency: dto.currency ?? 'NGN',
        status: dto.status ?? 'active',
      },
    });

    return serialize(goal);
  }

  async getGoals(userId: string) {
    const goals = await this.prisma.goal.findMany({
      where: { userId },
      orderBy: { createdAt: 'desc' },
    });

    return goals.map(serialize);
  }

  async getGoal(userId: string, goalId: string) {
    const goal = await this.prisma.goal.findFirst({
      where: { id: goalId, userId },
    });

    if (!goal) {
      throw new NotFoundException('Goal not found');
    }

    return serialize(goal);
  }

  async updateGoal(userId: string, goalId: string, dto: UpdateGoalDto) {
    const existing = await this.prisma.goal.findFirst({
      where: { id: goalId, userId },
    });

    if (!existing) {
      throw new NotFoundException('Goal not found');
    }

    const goal = await this.prisma.goal.update({
      where: { id: goalId },
      data: {
        ...(dto.name !== undefined && { name: dto.name }),
        ...(dto.target_amount !== undefined && { targetAmount: dto.target_amount }),
        ...(dto.current_amount !== undefined && { currentAmount: dto.current_amount }),
        ...(dto.target_date !== undefined && {
          targetDate: dto.target_date ? new Date(dto.target_date) : null,
        }),
        ...(dto.status !== undefined && { status: dto.status }),
      },
    });

    return serialize(goal);
  }
}
