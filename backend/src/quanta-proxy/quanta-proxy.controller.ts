import {
  Body,
  Controller,
  Get,
  Headers,
  Post,
  UploadedFile,
  UploadedFiles,
  UseGuards,
  UseInterceptors,
} from '@nestjs/common';
import { FileFieldsInterceptor, FileInterceptor } from '@nestjs/platform-express';
import { randomUUID } from 'crypto';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { QuantaProxyService } from './quanta-proxy.service';

interface UploadedMulterFile {
  buffer: Buffer;
  originalname: string;
  mimetype: string;
}

function toFilePayload(file?: UploadedMulterFile) {
  return file
    ? { buffer: file.buffer, filename: file.originalname, mimetype: file.mimetype }
    : undefined;
}

// Everything here sits behind the real user's JWT (JwtAuthGuard) - this is
// the trust boundary the Quanta proxy contract describes: we verify the
// human first, then speak to Quanta as a trusted machine caller using
// headers derived from that verified identity, never from the request body.
@UseGuards(JwtAuthGuard)
@Controller('quanta')
export class QuantaProxyController {
  constructor(private readonly quanta: QuantaProxyService) {}

  @Get('voice/status')
  voiceStatus(@CurrentUser() user: JwtPayload) {
    return this.quanta.voiceStatus(user.sub);
  }

  @Post('interact')
  interact(
    @CurrentUser() user: JwtPayload,
    @Headers('x-session-id') sessionId: string | undefined,
    @Headers('accept-language') locale: string | undefined,
    @Body() body: { text?: string; verification_threshold?: number; metadata?: Record<string, unknown> },
  ) {
    return this.quanta.interact(
      { userId: user.sub, sessionId: sessionId ?? randomUUID(), locale },
      body,
    );
  }

  @Post('interact/multipart')
  @UseInterceptors(
    FileFieldsInterceptor([
      { name: 'image', maxCount: 1 },
      { name: 'audio', maxCount: 1 },
      { name: 'voice_profile', maxCount: 1 },
    ]),
  )
  interactMultipart(
    @CurrentUser() user: JwtPayload,
    @Headers('x-session-id') sessionId: string | undefined,
    @Headers('accept-language') locale: string | undefined,
    @Body() body: { text?: string; verification_threshold?: string },
    @UploadedFiles()
    files: {
      image?: UploadedMulterFile[];
      audio?: UploadedMulterFile[];
      voice_profile?: UploadedMulterFile[];
    },
  ) {
    return this.quanta.interactMultipart(
      { userId: user.sub, sessionId: sessionId ?? randomUUID(), locale },
      {
        text: body.text,
        verification_threshold: body.verification_threshold
          ? Number(body.verification_threshold)
          : undefined,
        image: toFilePayload(files.image?.[0]),
        audio: toFilePayload(files.audio?.[0]),
        voice_profile: toFilePayload(files.voice_profile?.[0]),
      },
    );
  }

  @Post('voice/interact')
  @UseInterceptors(FileInterceptor('audio'))
  voiceInteract(
    @CurrentUser() user: JwtPayload,
    @Headers('x-session-id') sessionId: string | undefined,
    @Headers('accept-language') locale: string | undefined,
    @Body('verification_threshold') verificationThreshold: string | undefined,
    @UploadedFile() audio: UploadedMulterFile,
  ) {
    return this.quanta.voiceInteract(
      { userId: user.sub, sessionId: sessionId ?? randomUUID(), locale },
      { buffer: audio.buffer, filename: audio.originalname, mimetype: audio.mimetype },
      verificationThreshold ? Number(verificationThreshold) : undefined,
    );
  }

  @Post('voice/enroll')
  @UseInterceptors(FileInterceptor('audio'))
  voiceEnroll(
    @CurrentUser() user: JwtPayload,
    @Headers('x-session-id') sessionId: string | undefined,
    @Headers('accept-language') locale: string | undefined,
    @UploadedFile() audio: UploadedMulterFile,
  ) {
    return this.quanta.voiceEnroll(
      { userId: user.sub, sessionId: sessionId ?? randomUUID(), locale },
      { buffer: audio.buffer, filename: audio.originalname, mimetype: audio.mimetype },
    );
  }
}
