CREATE SEQUENCE invoice_seq;

-- CreateTable
CREATE TABLE "categories" (
    "category_id" SERIAL NOT NULL,
    "category_name" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "categories_pkey" PRIMARY KEY ("category_id")
);

-- CreateTable
CREATE TABLE "expenses" (
    "id" SERIAL NOT NULL,
    "invoice_no" TEXT DEFAULT ('INV-'::text || lpad((nextval('invoice_seq'::regclass))::text, 6, '0'::text)),
    "material_name" TEXT NOT NULL,
    "amount" DECIMAL(10,2) NOT NULL,
    "payment_method" TEXT NOT NULL,
    "advance_amount" DECIMAL(10,2) DEFAULT 0,
    "used" BOOLEAN DEFAULT false,
    "added_by" TEXT NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    "description" TEXT,
    "edited" BOOLEAN DEFAULT false,

    CONSTRAINT "expenses_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "inventory" (
    "id" SERIAL NOT NULL,
    "invoice_no" TEXT DEFAULT ('INV-'::text || lpad((nextval('invoice_seq'::regclass))::text, 6, '0'::text)),
    "category" TEXT NOT NULL,
    "product_name" TEXT NOT NULL,
    "cost_price" DECIMAL(10,2) NOT NULL,
    "quantity" INTEGER NOT NULL,
    "advance_amount" DECIMAL(10,2) DEFAULT 0,
    "added_by" TEXT NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    "edited" BOOLEAN DEFAULT false,

    CONSTRAINT "inventory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "sales" (
    "id" SERIAL NOT NULL,
    "invoice_no" TEXT DEFAULT ('INV-'::text || lpad((nextval('invoice_seq'::regclass))::text, 6, '0'::text)),
    "customer_name" TEXT NOT NULL,
    "customer_address" TEXT,
    "customer_phone" TEXT,
    "category" TEXT NOT NULL,
    "product_name" TEXT NOT NULL,
    "quantity" INTEGER NOT NULL,
    "cost_price" DECIMAL(10,2) NOT NULL,
    "sale_price" DECIMAL(10,2) NOT NULL,
    "payment_type" TEXT NOT NULL,
    "advance_amount" DECIMAL(10,2) DEFAULT 0,
    "sold_by" TEXT NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,
    "edited" BOOLEAN DEFAULT false,

    CONSTRAINT "sales_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" SERIAL NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "email" VARCHAR(100) NOT NULL,
    "password" VARCHAR(255) NOT NULL,
    "role_id" SMALLINT NOT NULL,
    "created_at" TIMESTAMP(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "categories_category_name_key" ON "categories"("category_name");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

