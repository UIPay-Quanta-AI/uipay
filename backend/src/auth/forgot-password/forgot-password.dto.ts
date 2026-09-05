import { IsEmail, IsNotEmpty, IsString, Matches } from 'class-validator';

export class ForgotPasswordDto {
  @IsEmail()
  @IsNotEmpty()
  email!: string;
}

export class ResetPasswordDto {
  @IsEmail()
  @IsNotEmpty()
  email!: string;

  @IsString()
  @IsNotEmpty()
  @Matches(/^\d{6}$/, {
    message: 'OTP must be exactly 6 digits',
  })
  otp!: string;

  @IsString()
  @Matches(/^(?=.*[A-Z])(?=.*[a-z])[^"'!.\-/\\|]{12,}$/, {
    message:
      'Password must be at least 12 characters, include an uppercase and a lowercase letter, and not contain " \' ! . - / \\ |',
  })
  newPassword!: string;
}
