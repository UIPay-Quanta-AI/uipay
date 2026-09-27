import {
  IsNotEmpty,
  IsNumber,
  IsPositive,
  IsString,
  IsUUID,
  Matches,
  Min,
} from 'class-validator';

export class TransferDto {
  @IsUUID()
  recipientId!: string;

  @IsNumber()
  @IsPositive()
  amount!: number;

  @Matches(/^\d{4}$/, { message: 'PIN must be exactly 4 digits' })
  pin!: string;
}

export class InitiateFundingDto {
  // NGN, not kobo - converted to kobo before we ever talk to Paystack
  @IsNumber()
  @Min(100, { message: 'Minimum funding amount is ₦100' })
  amount!: number;
}

export class VerifyFundingDto {
  @IsString()
  @IsNotEmpty()
  reference!: string;
}
