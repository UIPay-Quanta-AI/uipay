import { Module } from '@nestjs/common';
import { AppJwtModule } from '../auth/jwt/app-jwt.module';
import { PrismaModule } from '../prisma/prisma.module';
import { ProfileController } from './profile.controller';
import { ProfileService } from './profile.service';

@Module({
  imports: [PrismaModule, AppJwtModule],
  controllers: [ProfileController],
  providers: [ProfileService],
})
export class ProfileModule {}
