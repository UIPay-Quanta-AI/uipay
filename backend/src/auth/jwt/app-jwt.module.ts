import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AppJwtService } from './app-jwt.service';
import { JwtAuthGuard } from './jwt-auth.guard';

@Module({
  imports: [
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.getOrThrow<string>('JWT_ACCESS_SECRET'),
      }),
    }),
  ],
  providers: [AppJwtService, JwtAuthGuard],
  // JwtModule has to be re-exported too, otherwise JwtService isn't visible
  // to modules that import AppJwtModule just to use JwtAuthGuard
  exports: [AppJwtService, JwtAuthGuard, JwtModule],
})
export class AppJwtModule {}
