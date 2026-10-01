import { Controller, Get, Param, Query, UseGuards } from '@nestjs/common';
import { QuantaServiceAuthGuard } from './quanta-service-auth.guard';
import { TransactionsService } from './transactions.service';

@UseGuards(QuantaServiceAuthGuard)
@Controller('api/v1/users/:userId')
export class TransactionsController {
  constructor(private readonly service: TransactionsService) {}

  @Get('transactions')
  getTransactions(
    @Param('userId') userId: string,
    @Query('start_date') startDate?: string,
    @Query('end_date') endDate?: string,
  ) {
    return this.service.getTransactions(userId, startDate, endDate);
  }

  @Get('transaction-context')
  getTransactionContext() {
    return this.service.getTransactionContext();
  }
}
