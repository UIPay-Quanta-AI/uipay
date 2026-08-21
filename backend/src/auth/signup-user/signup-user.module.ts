import { Module } from '@nestjs/common';
import { SignupUserController } from './signup-user.controller';
import { SignupUserService } from './signup-user.service';
import { PrismaModule } from '../../prisma/prisma.module';
import { RedisModule } from '../../redis/redis.module';
import { EmailQueueModule } from '../../queue/email/email.module';
import { OtpModule } from '../otp/otp.module';
import { SessionModule } from '../session/session.module';
import { AppJwtModule } from '../jwt/app-jwt.module';
import { WalletModule } from '../../wallet/wallet.module';

@Module({
  imports: [
    PrismaModule,
    RedisModule,
    EmailQueueModule,
    OtpModule,
    SessionModule,
    AppJwtModule,
    WalletModule,
  ],
  controllers: [SignupUserController],
  providers: [SignupUserService],
})
export class SignupUserModule {}
