import { IsNotEmpty, IsNumber, IsPositive, IsString, Matches } from 'class-validator';

export class RegisterTagDto {
  @IsString()
  @IsNotEmpty()
  tagId!: string;
}

export class PayWithTagDto {
  @IsString()
  @IsNotEmpty()
  tagId!: string;

  @IsNumber()
  @IsPositive()
  amount!: number;

  @Matches(/^\d{4}$/, { message: 'PIN must be exactly 4 digits' })
  pin!: string;
}
