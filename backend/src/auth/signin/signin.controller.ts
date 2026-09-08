import { Body, Controller, Post, Req } from '@nestjs/common';
import { Request } from 'express';
import { SignInDto } from './signin.dto';
import { successResponse } from '../../common/response/success-response';
import { SignInService } from './signin.service';

@Controller('auth')
export class SignInController {
  constructor(private readonly service: SignInService) {}

  @Post('signin')
  async signIn(@Body() body: SignInDto, @Req() req: Request) {
    const tokens = await this.service.signIn(body, {
      userAgent: req.headers['user-agent'],
      ipAddress: req.ip,
    });

    return successResponse('Login successful', tokens);
  }
}
