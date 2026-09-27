import { Body, Controller, Get, Param, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { InitiateFundingDto, TransferDto, VerifyFundingDto } from './wallet.dto';
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

  @Get('resolve/:accountNumber')
  async resolveAccountNumber(
    @CurrentUser() user: JwtPayload,
    @Param('accountNumber') accountNumber: string,
  ) {
    const resolved = await this.service.resolveAccountNumber(
      accountNumber,
      user.sub,
    );

    return successResponse('Account resolved successfully', resolved);
  }

  @Post('transfer')
  async transfer(@CurrentUser() user: JwtPayload, @Body() body: TransferDto) {
    await this.service.verifyTransactionPin(user.sub, body.pin);
    const transaction = await this.service.transfer(user.sub, body);

    return successResponse('Transfer successful', transaction);
  }

  @Get('recent-recipients')
  async getRecentRecipients(@CurrentUser() user: JwtPayload) {
    const recipients = await this.service.getRecentRecipients(user.sub);

    return successResponse(
      'Recent recipients retrieved successfully',
      recipients,
    );
  }

  @Get('history')
  async getHistory(@CurrentUser() user: JwtPayload) {
    const history = await this.service.getHistory(user.sub);

    return successResponse(
      'Transaction history retrieved successfully',
      history,
    );
  }

  @Post('fund/initiate')
  async initiateFunding(
    @CurrentUser() user: JwtPayload,
    @Body() body: InitiateFundingDto,
  ) {
    const result = await this.service.initiateFunding(
      user.sub,
      user.email,
      body.amount,
    );

    return successResponse('Payment initialized', result);
  }

  @Post('fund/verify')
  async verifyFunding(
    @CurrentUser() user: JwtPayload,
    @Body() body: VerifyFundingDto,
  ) {
    const result = await this.service.verifyFunding(user.sub, body.reference);

    return successResponse('Funding status retrieved', result);
  }
}
