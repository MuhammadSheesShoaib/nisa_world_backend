-- AlterTable
ALTER TABLE "expenses" ADD COLUMN     "amount_taken" DECIMAL(10,2) DEFAULT 0,
ADD COLUMN     "payment_history" TEXT,
ADD COLUMN     "remaining_amount" DECIMAL(10,2),
ADD COLUMN     "total_amount" DECIMAL(10,2);
