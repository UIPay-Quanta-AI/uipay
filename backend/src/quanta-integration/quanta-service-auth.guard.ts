import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Request } from 'express';

// These routes are called by the Quanta microservice itself (machine-to-
// machine), not by a signed-in user's browser - there is no user JWT on
// these requests. Quanta authenticates with a shared secret bearer token
// (its own UIPAY_SERVICE_TOKEN config value) instead. The user_id in the
// URL is trusted because Quanta already established it from ITS OWN
// trusted caller (the Quanta Proxy, which verified the real user's JWT).
@Injectable()
export class QuantaServiceAuthGuard implements CanActivate {
  constructor(private readonly config: ConfigService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const authHeader = request.headers['authorization'];

    const expected = this.config.getOrThrow<string>('QUANTA_SERVICE_TOKEN');
    const provided =
      typeof authHeader === 'string' && authHeader.startsWith('Bearer ')
        ? authHeader.slice('Bearer '.length)
        : undefined;

    if (!provided || provided !== expected) {
      throw new UnauthorizedException('Invalid or missing Quanta service token');
    }

    return true;
  }
}
