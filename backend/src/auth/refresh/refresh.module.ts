import { Module } from '@nestjs/common';
import { PrismaModule } from '../../prisma/prisma.module';
import { AppJwtModule } from '../jwt/app-jwt.module';
import { SessionModule } from '../session/session.module';
import { RefreshController } from './refresh.controller';
import { RefreshService } from './refresh.service';

@Module({
  imports: [PrismaModule, SessionModule, AppJwtModule],
  controllers: [RefreshController],
  providers: [RefreshService],
})
export class RefreshModule {}
