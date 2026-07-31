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
          port: config.getOrThrow('REDIS_PORT'),
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
  ],
  providers: [AuthService, RedisService],
})
export class AppModule {}
