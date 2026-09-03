import { Body, Controller, Get, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { ApplyMerchantDto } from './merchant.dto';
import { MerchantService } from './merchant.service';

@UseGuards(JwtAuthGuard)
@Controller('merchant')
export class MerchantController {
  constructor(private readonly service: MerchantService) {}

  @Post('apply')
  async apply(@CurrentUser() user: JwtPayload, @Body() body: ApplyMerchantDto) {
    const merchant = await this.service.apply(user.sub, body);

    return successResponse(
      'Merchant application submitted successfully',
      merchant,
    );
  }

  @Get('profile')
  async getProfile(@CurrentUser() user: JwtPayload) {
    const merchant = await this.service.getProfile(user.sub);

    return successResponse('Merchant profile retrieved successfully', merchant);
  }

  @Get('transactions')
  async getTransactions(@CurrentUser() user: JwtPayload) {
    const transactions = await this.service.getTransactions(user.sub);

    return successResponse(
      'Merchant transactions retrieved successfully',
      transactions,
    );
  }

  @Get('balance')
  async getBalance(@CurrentUser() user: JwtPayload) {
    const balance = await this.service.getBalance(user.sub);

    return successResponse('Merchant balance retrieved successfully', balance);
  }
}
