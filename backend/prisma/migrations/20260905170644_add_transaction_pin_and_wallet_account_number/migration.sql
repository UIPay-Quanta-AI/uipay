-- AlterTable
ALTER TABLE "users" ADD COLUMN     "transaction_pin_hash" TEXT;

-- AlterTable
ALTER TABLE "wallets" ADD COLUMN     "account_number" TEXT;

-- CreateIndex
CREATE UNIQUE INDEX "wallets_account_number_key" ON "wallets"("account_number");

