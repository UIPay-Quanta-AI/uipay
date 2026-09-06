import { Body, Controller, Get, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { SetPinDto, VerifyIdDto } from './profile.dto';
import { ProfileService } from './profile.service';

@UseGuards(JwtAuthGuard)
@Controller('profile')
export class ProfileController {
  constructor(private readonly service: ProfileService) {}

  @Get('me')
  async getMe(@CurrentUser() user: JwtPayload) {
    const profile = await this.service.getMe(user.sub);

    return successResponse('Profile retrieved successfully', profile);
  }

  @Post('pin')
  async setPin(@CurrentUser() user: JwtPayload, @Body() body: SetPinDto) {
    const result = await this.service.setPin(user.sub, body);

    return successResponse('Transaction PIN set successfully', result);
  }

  @Post('verify-id')
  async verifyId(@CurrentUser() user: JwtPayload, @Body() body: VerifyIdDto) {
    const result = await this.service.verifyId(user.sub, body);

    return successResponse('Identity verified successfully', result);
  }
}
