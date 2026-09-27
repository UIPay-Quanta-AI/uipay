import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ValidationPipe } from '@nestjs/common';

const DEFAULT_LOCALHOST_ORIGINS = [
  'http://localhost:3000',
  'http://localhost:3001',
  'http://localhost:3002',
  'http://localhost:3003',
];

// matches http://<private LAN IP>:3000-3003 - covers phone/LAN dev testing
// automatically regardless of which network you're on, so switching wifi
// (which changes your machine's IP) doesn't need a FRONTEND_URLS update.
// Restricted to RFC1918 private ranges, so this can't be satisfied by a
// real public-internet origin.
const PRIVATE_LAN_DEV_ORIGIN =
  /^http:\/\/(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2}):300[0-3]$/;

async function bootstrap() {
  // rawBody: true keeps the exact request bytes on req.rawBody alongside
  // the normal parsed req.body - needed to verify Paystack's webhook
  // signature, which is computed over the raw bytes, not the parsed JSON.
  const app = await NestFactory.create(AppModule, { rawBody: true });

  const extraOrigins = process.env.FRONTEND_URLS?.split(',') ?? [];
  const allowedOrigins = [...DEFAULT_LOCALHOST_ORIGINS, ...extraOrigins];

  app.enableCors({
    origin: (
      origin: string | undefined,
      callback: (err: Error | null, allow?: boolean) => void,
    ) => {
      if (
        !origin ||
        allowedOrigins.includes(origin) ||
        PRIVATE_LAN_DEV_ORIGIN.test(origin)
      ) {
        callback(null, true);
      } else {
        callback(new Error(`Origin ${origin} not allowed by CORS`));
      }
    },
    credentials: true,
  });

  app.useGlobalPipes(new ValidationPipe());
  await app.listen(process.env.PORT ?? 3001);
}
bootstrap();
