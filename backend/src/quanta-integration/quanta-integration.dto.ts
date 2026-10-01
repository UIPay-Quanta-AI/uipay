import {
  IsDateString,
  IsEnum,
  IsNotEmpty,
  IsNumberString,
  IsOptional,
  IsString,
} from 'class-validator';

// Enum values match quanta/app/domain/financial_profile/models.py exactly -
// these are validated with Pydantic on Quanta's side after we return them.
export enum IncomeFrequency {
  MONTHLY = 'monthly',
  BIWEEKLY = 'biweekly',
  WEEKLY = 'weekly',
  IRREGULAR = 'irregular',
}

export enum EmploymentType {
  SALARIED = 'salaried',
  SELF_EMPLOYED = 'self_employed',
  FREELANCE = 'freelance',
  UNEMPLOYED = 'unemployed',
  OTHER = 'other',
}

export enum GoalStatus {
  ACTIVE = 'active',
  COMPLETED = 'completed',
  PAUSED = 'paused',
  CANCELLED = 'cancelled',
}

export class UpsertFinancialProfileDto {
  @IsOptional()
  @IsNumberString()
  monthly_income?: string;

  @IsOptional()
  @IsEnum(IncomeFrequency)
  income_frequency?: IncomeFrequency;

  @IsOptional()
  @IsEnum(EmploymentType)
  employment_type?: EmploymentType;

  @IsOptional()
  @IsNumberString()
  fixed_expenses?: string;

  @IsOptional()
  @IsNumberString()
  variable_expenses?: string;

  @IsOptional()
  @IsNumberString()
  savings_target?: string;

  @IsOptional()
  @IsString()
  currency?: string;
}

export class CreateGoalDto {
  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsNumberString()
  target_amount!: string;

  @IsOptional()
  @IsNumberString()
  current_amount?: string;

  @IsOptional()
  @IsDateString()
  target_date?: string;

  @IsOptional()
  @IsString()
  currency?: string;

  @IsOptional()
  @IsEnum(GoalStatus)
  status?: GoalStatus;
}

export class UpdateGoalDto {
  @IsOptional()
  @IsString()
  name?: string;

  @IsOptional()
  @IsNumberString()
  target_amount?: string;

  @IsOptional()
  @IsNumberString()
  current_amount?: string;

  @IsOptional()
  @IsDateString()
  target_date?: string;

  @IsOptional()
  @IsEnum(GoalStatus)
  status?: GoalStatus;
}

export class SaveBudgetDto {
  @IsDateString()
  start_date!: string;

  @IsDateString()
  end_date!: string;

  @IsOptional()
  @IsString()
  currency?: string;

  // Quanta's BudgetService sends the full computed budget shape on create;
  // the rest of the fields are accepted loosely here and stored as-is since
  // Quanta owns their structure (see docs/BUDGET.md) and we don't
  // re-validate business rules it has already applied.
  version?: number;
  status?: string;
  income_plan?: Record<string, unknown>;
  allocations?: Record<string, unknown>[];
  goal_allocations?: Record<string, unknown>[];
  total_allocated_expenses?: string;
  total_allocated_goals?: string;
  total_unallocated_income?: string;
  previous_version_id?: string;
  update_reason?: string;
}
