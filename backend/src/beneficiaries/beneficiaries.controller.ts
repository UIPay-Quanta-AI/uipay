import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseUUIDPipe,
  Post,
  UseGuards,
} from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { BeneficiariesService } from './beneficiaries.service';
import { CreateBeneficiaryDto } from './beneficiaries.dto';

@UseGuards(JwtAuthGuard)
@Controller('beneficiaries')
export class BeneficiariesController {
  constructor(private readonly service: BeneficiariesService) {}

  @Get()
  async findAll(@CurrentUser() user: JwtPayload) {
    const beneficiaries = await this.service.findAll(user.sub);

    return successResponse(
      'Beneficiaries retrieved successfully',
      beneficiaries,
    );
  }

  @Post()
  async create(
    @CurrentUser() user: JwtPayload,
    @Body() body: CreateBeneficiaryDto,
  ) {
    const beneficiary = await this.service.create(user.sub, body);

    return successResponse('Beneficiary added successfully', beneficiary);
  }

  @Delete(':id')
  async remove(
    @CurrentUser() user: JwtPayload,
    @Param('id', ParseUUIDPipe) id: string,
  ) {
    await this.service.remove(user.sub, id);

    return successResponse('Beneficiary removed successfully', null);
  }
}
