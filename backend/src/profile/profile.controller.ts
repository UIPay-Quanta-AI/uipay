import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseUUIDPipe,
  Patch,
  Post,
  UseGuards,
} from '@nestjs/common';
import { CurrentUser } from '../auth/jwt/current-user.decorator';
import { JwtAuthGuard } from '../auth/jwt/jwt-auth.guard';
import { JwtPayload } from '../auth/jwt/jwt-payload.interface';
import { successResponse } from '../common/response/success-response';
import {
  ChangePasswordDto,
  DeleteAccountDto,
  SetPinDto,
  UpdateNotificationPreferencesDto,
  VerifyIdDto,
  VerifyPinDto,
} from './profile.dto';
import { ProfileService } from './profile.service';

@UseGuards(JwtAuthGuard)
@Controller('profile')
export class ProfileController {
  constructor(private readonly service: ProfileService) {}

  @Get('me')
  async getMe(@CurrentUser() user: JwtPayload) {
    const profile = await this.service.getMe(user.sub);

    return successResponse('Profile retrieved successfully', profile);
  }

  @Post('pin')
  async setPin(@CurrentUser() user: JwtPayload, @Body() body: SetPinDto) {
    const result = await this.service.setPin(user.sub, body);

    return successResponse('Transaction PIN set successfully', result);
  }

  @Post('pin/verify')
  async verifyPin(@CurrentUser() user: JwtPayload, @Body() body: VerifyPinDto) {
    const result = await this.service.verifyPin(user.sub, body);

    return successResponse('PIN verified', result);
  }

  @Post('password')
  async changePassword(
    @CurrentUser() user: JwtPayload,
    @Body() body: ChangePasswordDto,
  ) {
    await this.service.changePassword(user.sub, body);

    return successResponse('Password changed successfully', null);
  }

  @Get('sessions')
  async listSessions(@CurrentUser() user: JwtPayload) {
    const sessions = await this.service.listSessions(user.sub);

    return successResponse('Sessions retrieved successfully', sessions);
  }

  @Delete('sessions/:id')
  async revokeSession(
    @CurrentUser() user: JwtPayload,
    @Param('id', ParseUUIDPipe) id: string,
  ) {
    await this.service.revokeSession(user.sub, id);

    return successResponse('Session revoked', null);
  }

  @Post('sessions/logout-all')
  async logoutAllDevices(@CurrentUser() user: JwtPayload) {
    await this.service.logoutAllDevices(user.sub);

    return successResponse('Logged out of all devices', null);
  }

  @Get('notification-preferences')
  async getNotificationPreferences(@CurrentUser() user: JwtPayload) {
    const preferences = await this.service.getNotificationPreferences(user.sub);

    return successResponse('Notification preferences retrieved', preferences);
  }

  @Patch('notification-preferences')
  async updateNotificationPreferences(
    @CurrentUser() user: JwtPayload,
    @Body() body: UpdateNotificationPreferencesDto,
  ) {
    const preferences = await this.service.updateNotificationPreferences(
      user.sub,
      body,
    );

    return successResponse('Notification preferences updated', preferences);
  }

  @Delete('me')
  async deleteAccount(
    @CurrentUser() user: JwtPayload,
    @Body() body: DeleteAccountDto,
  ) {
    await this.service.deleteAccount(user.sub, body);

    return successResponse('Account deleted', null);
  }

  @Post('verify-id')
  async verifyId(@CurrentUser() user: JwtPayload, @Body() body: VerifyIdDto) {
    const result = await this.service.verifyId(user.sub, body);

    return successResponse('Identity verified successfully', result);
  }
}
