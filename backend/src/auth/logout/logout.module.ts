import { Module } from '@nestjs/common';
import { SessionModule } from '../session/session.module';
import { LogoutController } from './logout.controller';
import { LogoutService } from './logout.service';

@Module({
  imports: [SessionModule],
  controllers: [LogoutController],
  providers: [LogoutService],
})
export class LogoutModule {}
