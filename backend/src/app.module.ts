import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { PrismaModule } from './prisma/prisma.module';
import { AuthService } from './auth/auth.service';
import { AuthModule } from './auth/auth.module';
import { RedisService } from './redis/redis.service';
import { RedisModule } from './redis/redis.module';
import { MailModule } from './mail/mail.module';
import { BullModule } from '@nestjs/bullmq';
import { EmailQueueModule } from './queue/email/email.module';
import { AppJwtModule } from './auth/jwt/app-jwt.module';
import { SessionModule } from './auth/session/session.module';
import { WalletModule } from './wallet/wallet.module';
import { BeneficiariesModule } from './beneficiaries/beneficiaries.module';
import { MerchantModule } from './merchant/merchant.module';
import { NfcModule } from './nfc/nfc.module';
import { QrModule } from './qr/qr.module';
import { AdminModule } from './admin/admin.module';
import { ProfileModule } from './profile/profile.module';

@Module({
  imports: [
    ConfigModule.forRoot({
      envFilePath: '.env',
      isGlobal: true,
    }),
    BullModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        connection: {
          host: config.getOrThrow('REDIS_HOST'),
          port: Number(config.getOrThrow('REDIS_PORT')),
          password: config.getOrThrow<string>('REDIS_PASSWORD'),
          // Upstash serves redis over TLS, same as the RedisService client
          tls: {},
        },
      }),
    }),
    AuthModule,
    PrismaModule,
    MailModule,
    RedisModule,
    EmailQueueModule,
    AppJwtModule,
    SessionModule,
    WalletModule,
    BeneficiariesModule,
    MerchantModule,
    NfcModule,
    QrModule,
    AdminModule,
    ProfileModule,
  ],
  providers: [AuthService, RedisService],
})
export class AppModule {}
