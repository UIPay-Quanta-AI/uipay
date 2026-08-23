import { IsEnum, IsOptional } from 'class-validator';

export enum MerchantApplicationStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
}

export enum TransactionPeriod {
  DAILY = 'daily',
  WEEKLY = 'weekly',
  MONTHLY = 'monthly',
}

export class ListMerchantsQueryDto {
  @IsOptional()
  @IsEnum(MerchantApplicationStatus)
  status?: MerchantApplicationStatus;
}

export class TransactionsQueryDto {
  @IsOptional()
  @IsEnum(TransactionPeriod)
  period?: TransactionPeriod;
}
