-- AlterTable
ALTER TABLE "users" ADD COLUMN "id_type" TEXT;
ALTER TABLE "users" ADD COLUMN "id_number" TEXT;
ALTER TABLE "users" ADD COLUMN "identity_verified_at" TIMESTAMP(3);
