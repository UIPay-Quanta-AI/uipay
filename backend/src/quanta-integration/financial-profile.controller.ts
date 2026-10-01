import { Body, Controller, Get, Param, Patch, Post, UseGuards } from '@nestjs/common';
import { QuantaServiceAuthGuard } from './quanta-service-auth.guard';
import { FinancialProfileService } from './financial-profile.service';
import { UpsertFinancialProfileDto } from './quanta-integration.dto';

@UseGuards(QuantaServiceAuthGuard)
@Controller('api/v1/users/:userId/profile')
export class FinancialProfileController {
  constructor(private readonly service: FinancialProfileService) {}

  @Get()
  getProfile(@Param('userId') userId: string) {
    return this.service.getProfile(userId);
  }

  @Post()
  createProfile(
    @Param('userId') userId: string,
    @Body() body: UpsertFinancialProfileDto,
  ) {
    return this.service.createProfile(userId, body);
  }

  @Patch()
  updateProfile(
    @Param('userId') userId: string,
    @Body() body: UpsertFinancialProfileDto,
  ) {
    return this.service.updateProfile(userId, body);
  }
}
