-- AlterTable
ALTER TABLE "users" ADD COLUMN "role" TEXT NOT NULL DEFAULT 'user';

-- AlterTable
ALTER TABLE "merchants" ADD COLUMN "status" TEXT NOT NULL DEFAULT 'pending';

-- carry over any already-approved merchants before dropping the old column
UPDATE "merchants" SET "status" = 'approved' WHERE "approved" = true;

-- AlterTable
ALTER TABLE "merchants" DROP COLUMN "approved";
