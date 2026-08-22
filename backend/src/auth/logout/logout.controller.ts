import { Body, Controller, Post } from '@nestjs/common';
import { successResponse } from '../../common/response/success-response';
import { LogoutDto } from './logout.dto';
import { LogoutService } from './logout.service';

@Controller('auth')
export class LogoutController {
  constructor(private readonly service: LogoutService) {}

  @Post('logout')
  async logout(@Body() body: LogoutDto) {
    await this.service.logout(body.refreshToken);

    return successResponse('Logged out successfully', null);
  }
}
