import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import {
  SEND_PASSWORD_RESET_EMAIL_JOB,
  SEND_VERIFICATION_EMAIL_JOB,
} from './constants';

@Injectable()
export class EmailQueueService {
  constructor(@InjectQueue('email') private readonly emailQueue: Queue) {}

  async sendVerification(email: string, otp: string) {
    await this.emailQueue.add(
      SEND_VERIFICATION_EMAIL_JOB,
      {
        email,
        otp,
      },
      {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
        removeOnComplete: 100,
        removeOnFail: 200,
      },
    );
  }

  async sendPasswordReset(email: string, otp: string) {
    await this.emailQueue.add(
      SEND_PASSWORD_RESET_EMAIL_JOB,
      {
        email,
        otp,
      },
      {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
        removeOnComplete: 100,
        removeOnFail: 200,
      },
    );
  }
}
