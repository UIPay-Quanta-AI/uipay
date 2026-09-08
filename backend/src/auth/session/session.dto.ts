export interface CreateSessionDto {
  userId: string;
  refreshTokenHash: string;
  expiresAt: Date;
  userAgent?: string;
  ipAddress?: string;
}
