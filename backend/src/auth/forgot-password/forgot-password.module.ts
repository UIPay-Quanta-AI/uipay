import { Module } from '@nestjs/common';
import { PrismaModule } from '../../prisma/prisma.module';
import { RedisModule } from '../../redis/redis.module';
import { EmailQueueModule } from '../../queue/email/email.module';
import { OtpModule } from '../otp/otp.module';
import { SessionModule } from '../session/session.module';
import { ForgotPasswordController } from './forgot-password.controller';
import { ForgotPasswordService } from './forgot-password.service';

@Module({
  imports: [
    PrismaModule,
    RedisModule,
    EmailQueueModule,
    OtpModule,
    SessionModule,
  ],
  controllers: [ForgotPasswordController],
  providers: [ForgotPasswordService],
})
export class ForgotPasswordModule {}
