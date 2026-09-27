import {
  Body,
  Controller,
  Get,
  Param,
  ParseUUIDPipe,
  Patch,
  Post,
  Query,
  UseGuards,
} from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { successResponse } from '../common/response/success-response';
import { AdminGuard } from './admin.guard';
import { AdminService } from './admin.service';
import {
  FlagTransactionDto,
  GenerateAdminQrDto,
  ListMerchantsQueryDto,
  RevenueQueryDto,
  TransactionsQueryDto,
} from './admin.dto';

@UseGuards(JwtAuthGuard, AdminGuard)
@Controller('admin')
export class AdminController {
  constructor(private readonly service: AdminService) {}

  @Get('users')
  async listUsers() {
    const users = await this.service.listUsers();

    return successResponse('Users retrieved successfully', users);
  }

  @Get('users/:id')
  async getUser(@Param('id', ParseUUIDPipe) id: string) {
    const user = await this.service.getUserDetail(id);

    return successResponse('User retrieved successfully', user);
  }

  @Get('users/:id/activity')
  async getUserActivity(@Param('id', ParseUUIDPipe) id: string) {
    const activity = await this.service.getUserActivity(id);

    return successResponse('User activity retrieved successfully', activity);
  }

  @Patch('users/:id/suspend')
  async suspendUser(@Param('id', ParseUUIDPipe) id: string) {
    const user = await this.service.suspendUser(id);

    return successResponse('User suspended successfully', user);
  }

  @Patch('users/:id/reactivate')
  async reactivateUser(@Param('id', ParseUUIDPipe) id: string) {
    const user = await this.service.reactivateUser(id);

    return successResponse('User reactivated successfully', user);
  }

  @Get('merchants')
  async listMerchants(@Query() query: ListMerchantsQueryDto) {
    const merchants = await this.service.listMerchants(query.status);

    return successResponse('Merchants retrieved successfully', merchants);
  }

  @Get('merchants/:id')
  async getMerchant(@Param('id', ParseUUIDPipe) id: string) {
    const merchant = await this.service.getMerchantDetail(id);

    return successResponse('Merchant retrieved successfully', merchant);
  }

  @Patch('merchants/:id/approve')
  async approveMerchant(@Param('id', ParseUUIDPipe) id: string) {
    const merchant = await this.service.approveMerchant(id);

    return successResponse('Merchant approved successfully', merchant);
  }

  @Patch('merchants/:id/reject')
  async rejectMerchant(@Param('id', ParseUUIDPipe) id: string) {
    const merchant = await this.service.rejectMerchant(id);

    return successResponse('Merchant rejected successfully', merchant);
  }

  @Get('revenue')
  async getRevenue(@Query() query: RevenueQueryDto) {
    const revenue = await this.service.getRevenue(query.period);

    return successResponse('Revenue retrieved successfully', revenue);
  }

  @Get('transactions')
  async getTransactions(@Query() query: TransactionsQueryDto) {
    const transactions = await this.service.getTransactions(query.period);

    return successResponse('Transactions retrieved successfully', transactions);
  }

  @Get('transactions/:id')
  async getTransaction(@Param('id', ParseUUIDPipe) id: string) {
    const transaction = await this.service.getTransactionDetail(id);

    return successResponse('Transaction retrieved successfully', transaction);
  }

  @Patch('transactions/:id/flag')
  async flagTransaction(
    @Param('id', ParseUUIDPipe) id: string,
    @Body() body: FlagTransactionDto,
  ) {
    const transaction = await this.service.flagTransaction(id, body.reason);

    return successResponse('Transaction flagged successfully', transaction);
  }

  @Get('nfc-qr-count')
  async getNfcQrCount() {
    const counts = await this.service.getNfcQrCount();

    return successResponse('NFC/QR counts retrieved successfully', counts);
  }

  @Post('qr/generate')
  async generateQr(@Body() body: GenerateAdminQrDto) {
    const qrCode = await this.service.generateQrForUser(
      body.recipientId,
      body.amount,
    );

    return successResponse('QR code generated successfully', qrCode);
  }
}
