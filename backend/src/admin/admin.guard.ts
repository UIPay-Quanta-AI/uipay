import {
  CanActivate,
  ExecutionContext,
  ForbiddenException,
  Injectable,
} from '@nestjs/common';
import { AuthenticatedRequest } from '../auth/jwt/authenticated-request.interface';
import { PrismaService } from '../prisma/prisma.service';

// this only checks the role, it doesn't verify the token, so it always needs
// to run after JwtAuthGuard has already set request.user
@Injectable()
export class AdminGuard implements CanActivate {
  constructor(private readonly prisma: PrismaService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest<AuthenticatedRequest>();

    const user = await this.prisma.user.findUnique({
      where: { id: request.user.sub },
    });

    if (!user || user.role !== 'admin') {
      throw new ForbiddenException('Admin access only');
    }

    return true;
  }
}
