import { execSync } from "node:child_process";
export default function () {
  process.env.DATABASE_URL = process.env.TEST_DATABASE_URL ?? "postgresql://postgres@localhost:5432/sb_test";
  execSync("npx prisma migrate reset --force --skip-seed --skip-generate", { stdio: "inherit", env: process.env });
}
