import { IsEnum, IsNotEmpty, IsString } from 'class-validator';

export enum MerchantApplicantType {
  INDIVIDUAL = 'individual',
  ORGANISATION = 'organisation',
}

export class ApplyMerchantDto {
  @IsEnum(MerchantApplicantType)
  applicantType!: MerchantApplicantType;

  @IsString()
  @IsNotEmpty()
  businessName!: string;

  @IsString()
  @IsNotEmpty()
  category!: string;
}
