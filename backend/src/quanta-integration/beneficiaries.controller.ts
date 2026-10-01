import { Controller, Get, Param, Query, UseGuards } from '@nestjs/common';
import { QuantaServiceAuthGuard } from './quanta-service-auth.guard';
import { QuantaBeneficiariesService } from './beneficiaries.service';

@UseGuards(QuantaServiceAuthGuard)
@Controller('api/v1/users/:userId/beneficiaries')
export class QuantaBeneficiariesController {
  constructor(private readonly service: QuantaBeneficiariesService) {}

  @Get()
  search(@Param('userId') userId: string, @Query('query') query?: string) {
    return this.service.search(userId, query);
  }
}
