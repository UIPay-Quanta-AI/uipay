import { Body, Controller, Get, Param, Post, UseGuards } from '@nestjs/common';
import { QuantaServiceAuthGuard } from './quanta-service-auth.guard';
import { BudgetsService } from './budgets.service';
import { SaveBudgetDto } from './quanta-integration.dto';

@UseGuards(QuantaServiceAuthGuard)
@Controller('api/v1/users/:userId/budgets')
export class BudgetsController {
  constructor(private readonly service: BudgetsService) {}

  @Post()
  saveBudget(@Param('userId') userId: string, @Body() body: SaveBudgetDto) {
    return this.service.saveBudget(userId, body);
  }

  @Get('current')
  getCurrentBudget(@Param('userId') userId: string) {
    return this.service.getCurrentBudget(userId);
  }

  @Get()
  getBudgetHistory(@Param('userId') userId: string) {
    return this.service.getBudgetHistory(userId);
  }
}
