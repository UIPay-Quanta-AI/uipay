import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import { VerifyIdDto } from './profile.dto';
import { ProfileService } from './profile.service';

@UseGuards(JwtAuthGuard)
@Controller('profile')
export class ProfileController {
  constructor(private readonly service: ProfileService) {}

  @Post('verify-id')
  async verifyId(@CurrentUser() user: JwtPayload, @Body() body: VerifyIdDto) {
    const result = await this.service.verifyId(user.sub, body);

    return successResponse('Identity verified successfully', result);
  }
}
