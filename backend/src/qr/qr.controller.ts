import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { GenerateQrDto, PayWithQrDto, ValidateQrDto } from './qr.dto';
import { QrService } from './qr.service';

@UseGuards(JwtAuthGuard)
@Controller('qr')
export class QrController {
  constructor(private readonly service: QrService) {}

  @Post('generate')
  async generate(
    @CurrentUser() user: JwtPayload,
    @Body() body: GenerateQrDto,
  ) {
    const qrCode = await this.service.generate(user.sub, body);

    return successResponse('QR code generated successfully', qrCode);
  }

  @Post('validate')
  async validate(@Body() body: ValidateQrDto) {
    const merchant = await this.service.validate(body.qrCode);

    return successResponse('QR code validated successfully', merchant);
  }

  @Post('pay')
  async pay(@CurrentUser() user: JwtPayload, @Body() body: PayWithQrDto) {
    const transaction = await this.service.pay(user.sub, body);

    return successResponse('Payment successful', transaction);
  }
}
