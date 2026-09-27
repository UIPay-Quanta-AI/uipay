import { Module } from '@nestjs/common';
import { AppJwtModule } from '../auth/jwt/app-jwt.module';
import { PrismaModule } from '../prisma/prisma.module';
import { PaystackService } from './paystack.service';
import { WalletController } from './wallet.controller';
import { WalletWebhookController } from './wallet-webhook.controller';
import { WalletService } from './wallet.service';

@Module({
  imports: [PrismaModule, AppJwtModule],
  controllers: [WalletController, WalletWebhookController],
  providers: [WalletService, PaystackService],
  exports: [WalletService],
})
export class WalletModule {}
