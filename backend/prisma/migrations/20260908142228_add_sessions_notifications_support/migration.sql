-- AlterTable
ALTER TABLE "session" ADD COLUMN     "ipAddress" TEXT,
ADD COLUMN     "userAgent" TEXT;

-- AlterTable
ALTER TABLE "users" ADD COLUMN     "notify_card_transactions" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "notify_general" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "notify_others" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "notify_sms_alerts" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "notify_transfers" BOOLEAN NOT NULL DEFAULT true;

-- CreateTable
CREATE TABLE "support_messages" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "message" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "support_messages_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "support_messages_user_id_idx" ON "support_messages"("user_id");

-- AddForeignKey
ALTER TABLE "support_messages" ADD CONSTRAINT "support_messages_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

