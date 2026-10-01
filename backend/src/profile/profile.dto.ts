import {
  IsBoolean,
  IsEnum,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
} from 'class-validator';

export class UpdateProfileDto {
  @IsOptional()
  @IsString()
  @IsNotEmpty()
  firstName?: string;

  @IsOptional()
  @IsString()
  @IsNotEmpty()
  lastName?: string;

  // same format already stored at signup (+234 prefix) - see SignupUserDto
  @IsOptional()
  @Matches(/^(?:\+234|234|0)[789][01]\d{8}$/, {
    message: 'Please enter a valid Nigerian phone number',
  })
  phoneNumber?: string;
}

export class SetPinDto {
  @Matches(/^\d{4}$/, { message: 'PIN must be exactly 4 digits' })
  pin!: string;
}

export class VerifyPinDto {
  @Matches(/^\d{4}$/, { message: 'PIN must be exactly 4 digits' })
  pin!: string;
}

export class ChangePasswordDto {
  @IsString()
  @IsNotEmpty()
  currentPassword!: string;

  @IsString()
  @Matches(/^(?=.*[A-Z])(?=.*[a-z])[^"'!.\-/\\|]{12,}$/, {
    message:
      'Password must be at least 12 characters, include an uppercase and a lowercase letter, and not contain " \' ! . - / \\ |',
  })
  newPassword!: string;
}

export class DeleteAccountDto {
  @IsString()
  @IsNotEmpty()
  password!: string;
}

export class UpdateNotificationPreferencesDto {
  @IsOptional()
  @IsBoolean()
  notifyGeneral?: boolean;

  @IsOptional()
  @IsBoolean()
  notifySmsAlerts?: boolean;

  @IsOptional()
  @IsBoolean()
  notifyCardTransactions?: boolean;

  @IsOptional()
  @IsBoolean()
  notifyTransfers?: boolean;

  @IsOptional()
  @IsBoolean()
  notifyOthers?: boolean;
}

export enum VerifiedIdType {
  NIN = 'nin',
  BVN = 'bvn',
}

export class VerifyIdDto {
  @IsEnum(VerifiedIdType)
  idType!: VerifiedIdType;

  @Matches(/^\d{11}$/, { message: 'ID number must be exactly 11 digits' })
  idNumber!: string;
}
