import { Body, Controller, Post } from '@nestjs/common';
import { SignInDto } from './signin.dto';
import { successResponse } from '../../common/response/success-response';
import { SignInService } from './signin.service';

@Controller('auth')
export class SignInController {
  constructor(private readonly service: SignInService) {}

  @Post('signin')
  async signIn(@Body() body: SignInDto) {
    const tokens = await this.service.signIn(body);

    return successResponse('Login successful', tokens);
  }
}
