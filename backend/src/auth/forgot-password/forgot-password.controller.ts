import { Body, Controller, Post } from '@nestjs/common';
import { successResponse } from '../../common/response/success-response';
import { ForgotPasswordDto, ResetPasswordDto } from './forgot-password.dto';
import { ForgotPasswordService } from './forgot-password.service';

@Controller('auth')
export class ForgotPasswordController {
  constructor(private readonly service: ForgotPasswordService) {}

  @Post('forgot-password')
  async forgotPassword(@Body() body: ForgotPasswordDto) {
    await this.service.forgotPassword(body);

    return successResponse('Password reset code sent successfully', null);
  }

  @Post('reset-password')
  async resetPassword(@Body() body: ResetPasswordDto) {
    await this.service.resetPassword(body);

    return successResponse('Password reset successfully', null);
  }
}
