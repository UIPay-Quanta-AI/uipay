-- CreateTable
CREATE TABLE "wallet_fundings" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "reference" TEXT NOT NULL,
    "amount" DECIMAL(18,2) NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "wallet_fundings_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "wallet_fundings_reference_key" ON "wallet_fundings"("reference");

-- CreateIndex
CREATE INDEX "wallet_fundings_user_id_idx" ON "wallet_fundings"("user_id");

-- AddForeignKey
ALTER TABLE "wallet_fundings" ADD CONSTRAINT "wallet_fundings_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
