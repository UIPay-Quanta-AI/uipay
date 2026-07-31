export interface CreateSessionDto {
  userId: string;
  refreshTokenHash: string;
  expiresAt: Date;
}
