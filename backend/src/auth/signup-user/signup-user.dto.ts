import {
  IsEmail,
  IsNotEmpty,
  IsOptional,
  IsString,
  Matches,
} from 'class-validator';

export class SignupUserDto {
  @IsEmail()
  emailAddress!: string;

  @IsString()
  password!: string;

  @IsString()
  firstName!: string;

  @IsString()
  lastName!: string;

  @IsOptional()
  @IsString()
  middleName?: string;

  @IsString()
  dob!: string;

  @Matches(/^(?:\+234|234|0)[789][01]\d{8}$/, {
    message: 'Please enter a valid Nigerian phone number',
  })
  phoneNumber!: string;
}

export class VerifyOtpDto {
  @IsEmail()
  @IsNotEmpty()
  emailAddress!: string;

  @IsString()
  @IsNotEmpty()
  @Matches(/^\d{6}$/, {
    message: 'OTP must be exactly 6 digits',
  })
  otp!: string;
}
