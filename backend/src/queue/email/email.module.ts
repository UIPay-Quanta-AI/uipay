import { Module } from '@nestjs/common';
import { EmailProcessor } from './email.processor';
import { EmailQueue } from './email.queue';
import { EmailQueueService } from './email.service';
import { MailModule } from '../../mail/mail.module';

@Module({
  imports: [EmailQueue, MailModule],
  providers: [EmailProcessor, EmailQueueService],
  exports: [EmailQueueService],
})
export class EmailQueueModule {}
