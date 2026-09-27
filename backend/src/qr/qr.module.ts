import { Module } from '@nestjs/common';
import { AppJwtModule } from '../auth/jwt/app-jwt.module';
import { PrismaModule } from '../prisma/prisma.module';
import { RedisModule } from '../redis/redis.module';
import { WalletModule } from '../wallet/wallet.module';
import { QrController } from './qr.controller';
import { QrService } from './qr.service';

@Module({
  imports: [PrismaModule, AppJwtModule, RedisModule, WalletModule],
  controllers: [QrController],
  providers: [QrService],
  exports: [QrService],
})
export class QrModule {}
