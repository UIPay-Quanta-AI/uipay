import { Module } from '@nestjs/common';
import { AppJwtModule } from '../auth/jwt/app-jwt.module';
import { SessionModule } from '../auth/session/session.module';
import { PrismaModule } from '../prisma/prisma.module';
import { QrModule } from '../qr/qr.module';
import { WalletModule } from '../wallet/wallet.module';
import { AdminController } from './admin.controller';
import { AdminGuard } from './admin.guard';
import { AdminService } from './admin.service';

@Module({
  imports: [PrismaModule, AppJwtModule, WalletModule, QrModule, SessionModule],
  controllers: [AdminController],
  providers: [AdminService, AdminGuard],
})
export class AdminModule {}
