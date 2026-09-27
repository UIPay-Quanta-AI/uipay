import {
  IsEnum,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsPositive,
  IsString,
} from 'class-validator';

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

export enum TransactionFlagReason {
  MISMATCH = 'mismatch',
  WRONG_CATEGORY = 'wrong_category',
  MALICIOUS_ACTIVITY = 'malicious_activity',
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

export class RevenueQueryDto {
  @IsOptional()
  @IsEnum(TransactionPeriod)
  period?: TransactionPeriod;
}

export class FlagTransactionDto {
  @IsEnum(TransactionFlagReason)
  reason!: TransactionFlagReason;
}

export class GenerateAdminQrDto {
  @IsString()
  @IsNotEmpty()
  recipientId!: string;

  @IsNumber()
  @IsPositive()
  amount!: number;
}
