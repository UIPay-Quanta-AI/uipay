import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { QuantaServiceAuthGuard } from './quanta-service-auth.guard';
import { FinancialProfileController } from './financial-profile.controller';
import { FinancialProfileService } from './financial-profile.service';
import { GoalsController } from './goals.controller';
import { GoalsService } from './goals.service';
import { BudgetsController } from './budgets.controller';
import { BudgetsService } from './budgets.service';
import { TransactionsController } from './transactions.controller';
import { TransactionsService } from './transactions.service';
import { QuantaBeneficiariesController } from './beneficiaries.controller';
import { QuantaBeneficiariesService } from './beneficiaries.service';

// The machine-to-machine API surface Quanta's RealUIPayClient calls
// (see quanta/docs/uipay-client-contract.md). Every route here is guarded
// by QuantaServiceAuthGuard, not JwtAuthGuard - there is no signed-in user
// on these requests, only Quanta authenticating with a shared secret.
@Module({
  imports: [PrismaModule],
  controllers: [
    FinancialProfileController,
    GoalsController,
    BudgetsController,
    TransactionsController,
    QuantaBeneficiariesController,
  ],
  providers: [
    QuantaServiceAuthGuard,
    FinancialProfileService,
    GoalsService,
    BudgetsService,
    TransactionsService,
    QuantaBeneficiariesService,
  ],
})
export class QuantaIntegrationModule {}
