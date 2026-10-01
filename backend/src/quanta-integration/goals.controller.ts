import { Body, Controller, Get, Param, Patch, Post, UseGuards } from '@nestjs/common';
import { QuantaServiceAuthGuard } from './quanta-service-auth.guard';
import { GoalsService } from './goals.service';
import { CreateGoalDto, UpdateGoalDto } from './quanta-integration.dto';

@UseGuards(QuantaServiceAuthGuard)
@Controller('api/v1/users/:userId/goals')
export class GoalsController {
  constructor(private readonly service: GoalsService) {}

  @Post()
  createGoal(@Param('userId') userId: string, @Body() body: CreateGoalDto) {
    return this.service.createGoal(userId, body);
  }

  @Get()
  getGoals(@Param('userId') userId: string) {
    return this.service.getGoals(userId);
  }

  @Get(':goalId')
  getGoal(@Param('userId') userId: string, @Param('goalId') goalId: string) {
    return this.service.getGoal(userId, goalId);
  }

  @Patch(':goalId')
  updateGoal(
    @Param('userId') userId: string,
    @Param('goalId') goalId: string,
    @Body() body: UpdateGoalDto,
  ) {
    return this.service.updateGoal(userId, goalId, body);
  }
}
