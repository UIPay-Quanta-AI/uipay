import { Processor, WorkerHost } from '@nestjs/bullmq';
import { Injectable, Logger } from '@nestjs/common';
import { ResendService } from '../../mail/resend.service';
import { Job } from 'bullmq';

@Injectable()
@Processor('email')
export class EmailProcessor extends WorkerHost {
  private readonly logger = new Logger(EmailProcessor.name);

  constructor(private readonly resendService: ResendService) {
    super();
  }

  async process(job: Job) {
    switch (job.name) {
      case 'send-verification-email': {
        const { email, otp } = job.data;

        await this.resendService.sendOtpEmail(email, otp);
        break;
      }

      default:
        this.logger.warn(`Unknown job: ${job.name}`);
    }
  }
}
