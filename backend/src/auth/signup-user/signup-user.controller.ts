import { Body, Controller, Post, Req } from '@nestjs/common';
import { Request } from 'express';
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
  async verifyEmail(@Body() body: VerifyOtpDto, @Req() req: Request) {
    const tokens = await this.service.verifyOtp(body.emailAddress, body.otp, {
      userAgent: req.headers['user-agent'],
      ipAddress: req.ip,
    });

    return successResponse('Email verified successfully.', tokens);
  }
}
