import { Body, Controller, Get, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { TransferDto } from './wallet.dto';
import { WalletService } from './wallet.service';

@UseGuards(JwtAuthGuard)
@Controller('wallet')
export class WalletController {
  constructor(private readonly service: WalletService) {}

  @Get('balance')
  async getBalance(@CurrentUser() user: JwtPayload) {
    const balance = await this.service.getBalance(user.sub);

    return successResponse('Balance retrieved successfully', balance);
  }

  @Get('account-number')
  async getAccountNumber(@CurrentUser() user: JwtPayload) {
    const accountNumber = await this.service.getAccountNumber(user.sub);

    return successResponse(
      'Account number retrieved successfully',
      accountNumber,
    );
  }

  @Post('transfer')
  async transfer(@CurrentUser() user: JwtPayload, @Body() body: TransferDto) {
    const transaction = await this.service.transfer(user.sub, body);

    return successResponse('Transfer successful', transaction);
  }

  @Get('history')
  async getHistory(@CurrentUser() user: JwtPayload) {
    const history = await this.service.getHistory(user.sub);

    return successResponse(
      'Transaction history retrieved successfully',
      history,
    );
  }
}
