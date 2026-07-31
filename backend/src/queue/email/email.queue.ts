import { BullModule } from '@nestjs/bullmq';
import { EMAIL_QUEUE } from './constants';

export const EmailQueue = BullModule.registerQueue({
  name: EMAIL_QUEUE,
});
