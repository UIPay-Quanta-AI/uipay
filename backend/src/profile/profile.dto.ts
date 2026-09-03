import { IsEnum, Matches } from 'class-validator';

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
