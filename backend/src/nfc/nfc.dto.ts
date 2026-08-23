import { IsNotEmpty, IsNumber, IsPositive, IsString } from 'class-validator';

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
}
