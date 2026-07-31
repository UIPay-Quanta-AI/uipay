import { Module } from '@nestjs/common';
import { SignInService } from './signin.service';
import { PrismaModule } from '../../prisma/prisma.module';
import { SessionModule } from '../session/session.module';
import { AppJwtModule } from '../jwt/app-jwt.module';
import { SignInController } from './signin.controller';

@Module({
  imports: [PrismaModule, SessionModule, AppJwtModule],
  providers: [SignInService],
  controllers: [SignInController],
})
export class SignInModule {}
