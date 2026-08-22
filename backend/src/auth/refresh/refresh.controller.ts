import { Body, Controller, Post } from '@nestjs/common';
import { successResponse } from '../../common/response/success-response';
import { RefreshDto } from './refresh.dto';
import { RefreshService } from './refresh.service';

@Controller('auth')
export class RefreshController {
  constructor(private readonly service: RefreshService) {}

  @Post('refresh')
  async refresh(@Body() body: RefreshDto) {
    const tokens = await this.service.refresh(body.refreshToken);

    return successResponse('Access token refreshed successfully', tokens);
  }
}
