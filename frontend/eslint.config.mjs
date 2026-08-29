import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // shadcn-generated primitives are vendor-equivalent; custom product code remains linted.
    "src/components/ui/**",
    "src/hooks/use-mobile.ts",
    "src/types/api.generated.ts",
  ]),
]);

export default eslintConfig;
