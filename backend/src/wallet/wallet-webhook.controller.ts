import {
  BadRequestException,
  Controller,
  Headers,
  HttpCode,
  Logger,
  Post,
  RawBodyRequest,
  Req,
} from '@nestjs/common';
import { Request } from 'express';
import { PaystackService } from './paystack.service';
import { WalletService } from './wallet.service';

// Deliberately its own controller, with no JwtAuthGuard - Paystack calls
// this directly from their servers, not from a signed-in browser session.
// The x-paystack-signature header is the only thing authenticating this
// request; see PaystackService.verifyWebhookSignature.
@Controller('wallet')
export class WalletWebhookController {
  private readonly logger = new Logger(WalletWebhookController.name);

  constructor(
    private readonly walletService: WalletService,
    private readonly paystackService: PaystackService,
  ) {}

  @Post('webhook')
  @HttpCode(200)
  async handleWebhook(
    @Req() req: RawBodyRequest<Request>,
    @Headers('x-paystack-signature') signature: string | undefined,
  ) {
    const rawBody = req.rawBody;
    if (!rawBody) {
      throw new BadRequestException('Missing request body');
    }

    if (!this.paystackService.verifyWebhookSignature(rawBody, signature)) {
      this.logger.warn('Rejected webhook call with an invalid signature');
      throw new BadRequestException('Invalid signature');
    }

    const event = JSON.parse(rawBody.toString('utf8'));
    await this.walletService.handlePaystackWebhookEvent(event);

    // Paystack just wants a 200 quickly - the body content doesn't matter.
    return { received: true };
  }
}
