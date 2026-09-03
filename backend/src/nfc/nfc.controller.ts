import { Body, Controller, Get, Param, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { PayWithTagDto, RegisterTagDto } from './nfc.dto';
import { NfcService } from './nfc.service';

@UseGuards(JwtAuthGuard)
@Controller('nfc')
export class NfcController {
  constructor(private readonly service: NfcService) {}

  @Post('register')
  async register(
    @CurrentUser() user: JwtPayload,
    @Body() body: RegisterTagDto,
  ) {
    const tag = await this.service.register(user.sub, body);

    return successResponse('Tag registered successfully', tag);
  }

  @Get('resolve/:tag_id')
  async resolve(@Param('tag_id') tagId: string) {
    const merchant = await this.service.resolve(tagId);

    return successResponse('Tag resolved successfully', merchant);
  }

  @Post('pay')
  async pay(@CurrentUser() user: JwtPayload, @Body() body: PayWithTagDto) {
    const transaction = await this.service.pay(user.sub, body);

    return successResponse('Payment successful', transaction);
  }
}
