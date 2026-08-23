import {
  IsEnum,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsPositive,
  IsString,
  ValidateIf,
} from 'class-validator';

export enum QrCodeType {
  STATIC = 'static',
  DYNAMIC = 'dynamic',
}

export class GenerateQrDto {
  @IsEnum(QrCodeType)
  type!: QrCodeType;

  @ValidateIf((dto: GenerateQrDto) => dto.type === QrCodeType.DYNAMIC)
  @IsNumber()
  @IsPositive()
  amount?: number;
}

export class ValidateQrDto {
  @IsString()
  @IsNotEmpty()
  qrCode!: string;
}

export class PayWithQrDto {
  @IsString()
  @IsNotEmpty()
  qrCode!: string;

  @IsOptional()
  @IsNumber()
  @IsPositive()
  amount?: number;
}
