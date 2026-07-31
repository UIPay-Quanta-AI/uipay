import { Module } from '@nestjs/common';

import { SignupUserModule } from './signup-user/signup-user.module';
import { OtpService } from './otp/otp.service';
import { SignInModule } from './signin/signin.module';

@Module({
  imports: [SignInModule, SignupUserModule],
  providers: [OtpService],
})
export class AuthModule {}
