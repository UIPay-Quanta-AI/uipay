import { IsNotEmpty, IsString, Matches } from 'class-validator';

export class CreateBeneficiaryDto {
  @IsString()
  @IsNotEmpty()
  nickname!: string;

  @Matches(/^\d{10}$/, {
    message: 'Account number must be exactly 10 digits',
  })
  accountNumber!: string;

  @IsString()
  @IsNotEmpty()
  bankName!: string;
}
