import { Module } from '@nestjs/common';

import { SignupUserModule } from './signup-user/signup-user.module';
import { OtpService } from './otp/otp.service';
import { SignInModule } from './signin/signin.module';
import { ForgotPasswordModule } from './forgot-password/forgot-password.module';
import { RefreshModule } from './refresh/refresh.module';
import { LogoutModule } from './logout/logout.module';

@Module({
  imports: [
    SignInModule,
    SignupUserModule,
    ForgotPasswordModule,
    RefreshModule,
    LogoutModule,
  ],
  providers: [OtpService],
})
export class AuthModule {}
