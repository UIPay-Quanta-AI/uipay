import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { CreateSupportMessageDto } from './support.dto';
import { SupportService } from './support.service';

@UseGuards(JwtAuthGuard)
@Controller('support')
export class SupportController {
  constructor(private readonly service: SupportService) {}

  @Post('messages')
  async create(
    @CurrentUser() user: JwtPayload,
    @Body() body: CreateSupportMessageDto,
  ) {
    const message = await this.service.create(user.sub, body);

    return successResponse('Message received', message);
  }
}
