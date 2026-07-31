import { Body, Controller, Post } from '@nestjs/common';
import { SignupUserService } from './signup-user.service';
import { SignupUserDto, VerifyOtpDto } from './signup-user.dto';
import { successResponse } from '../../common/response/success-response';

@Controller('auth')
export class SignupUserController {
  constructor(private readonly service: SignupUserService) {}

  @Post('register')
  async RegisterUser(@Body() body: SignupUserDto) {
    await this.service.signupUser(body);

    return successResponse('Verification code sent successfully', null);
  }

  @Post('verify-email')
  async verifyEmail(@Body() body: VerifyOtpDto) {
    const tokens = await this.service.verifyOtp(body.emailAddress, body.otp);

    return successResponse('Email verified successfully.', tokens);
  }
}
