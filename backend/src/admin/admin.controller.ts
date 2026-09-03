import {
  Controller,
  Get,
  Param,
  ParseUUIDPipe,
  Patch,
  Query,
  UseGuards,
} from '@nestjs/common';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { successResponse } from '../common/response/success-response';
import { AdminGuard } from './admin.guard';
import { AdminService } from './admin.service';
import { ListMerchantsQueryDto, TransactionsQueryDto } from './admin.dto';

@UseGuards(JwtAuthGuard, AdminGuard)
@Controller('admin')
export class AdminController {
  constructor(private readonly service: AdminService) {}

  @Get('users')
  async listUsers() {
    const users = await this.service.listUsers();

    return successResponse('Users retrieved successfully', users);
  }

  @Get('merchants')
  async listMerchants(@Query() query: ListMerchantsQueryDto) {
    const merchants = await this.service.listMerchants(query.status);

    return successResponse('Merchants retrieved successfully', merchants);
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
  async getRevenue() {
    const revenue = await this.service.getRevenue();

    return successResponse('Revenue retrieved successfully', revenue);
  }

  @Get('transactions')
  async getTransactions(@Query() query: TransactionsQueryDto) {
    const transactions = await this.service.getTransactions(query.period);

    return successResponse('Transactions retrieved successfully', transactions);
  }

  @Get('nfc-qr-count')
  async getNfcQrCount() {
    const counts = await this.service.getNfcQrCount();

    return successResponse('NFC/QR counts retrieved successfully', counts);
  }
}
