import { Module } from '@nestjs/common';
import { AppJwtModule } from '../auth/jwt/app-jwt.module';
import { PrismaModule } from '../prisma/prisma.module';
import { QuantaProxyController } from './quanta-proxy.controller';
import { QuantaProxyService } from './quanta-proxy.service';

// The authenticated gateway between the frontend and the Quanta
// microservice (see quanta/docs/proxy-integration-contract.md). Distinct
// from quanta-integration/, which is the reverse direction: Quanta calling
// back into us as a trusted machine caller.
@Module({
  imports: [PrismaModule, AppJwtModule],
  controllers: [QuantaProxyController],
  providers: [QuantaProxyService],
})
export class QuantaProxyModule {}
