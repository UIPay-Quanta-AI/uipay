-- AlterTable
ALTER TABLE "merchants" ADD COLUMN "applicant_type" TEXT NOT NULL DEFAULT 'individual';

-- AlterTable
ALTER TABLE "merchants" ALTER COLUMN "qr_code_url" DROP NOT NULL;
