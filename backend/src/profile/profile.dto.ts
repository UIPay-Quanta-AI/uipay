import { IsEnum, Matches } from 'class-validator';

export class SetPinDto {
  @Matches(/^\d{4}$/, { message: 'PIN must be exactly 4 digits' })
  pin!: string;
}

export enum VerifiedIdType {
  NIN = 'nin',
  BVN = 'bvn',
}

export class VerifyIdDto {
  @IsEnum(VerifiedIdType)
  idType!: VerifiedIdType;

  @Matches(/^\d{11}$/, { message: 'ID number must be exactly 11 digits' })
  idNumber!: string;
}
