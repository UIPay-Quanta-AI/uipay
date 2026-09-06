import { IsNumber, IsPositive, IsUUID, Matches } from 'class-validator';

export class TransferDto {
  @IsUUID()
  recipientId!: string;

  @IsNumber()
  @IsPositive()
  amount!: number;

  @Matches(/^\d{4}$/, { message: 'PIN must be exactly 4 digits' })
  pin!: string;
}
