import { IsNumber, IsPositive, IsUUID } from 'class-validator';

export class TransferDto {
  @IsUUID()
  recipientId!: string;

  @IsNumber()
  @IsPositive()
  amount!: number;
}
