import { Module } from '@nestjs/common';
import { AppJwtModule } from '../auth/jwt/app-jwt.module';
import { SessionModule } from '../auth/session/session.module';
import { PrismaModule } from '../prisma/prisma.module';
import { ProfileController } from './profile.controller';
import { ProfileService } from './profile.service';

@Module({
  imports: [PrismaModule, AppJwtModule, SessionModule],
  controllers: [ProfileController],
  providers: [ProfileService],
})
export class ProfileModule {}
