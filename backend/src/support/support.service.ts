import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateSupportMessageDto } from './support.dto';

@Injectable()
export class SupportService {
  constructor(private readonly prisma: PrismaService) {}

  // no live chat or admin viewer wired up yet - this just persists the
  // message so it exists somewhere real instead of vanishing into a fake
  // "sent!" toast
  async create(userId: string, dto: CreateSupportMessageDto) {
    return this.prisma.supportMessage.create({
      data: { userId, type: dto.type, message: dto.message },
    });
  }
}
