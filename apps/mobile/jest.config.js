module.exports = {
  preset: "jest-expo",
  collectCoverageFrom: [
    "src/lib/{api,auth-session,receipt-client,token-vault,validation}.ts",
    "!src/**/*.d.ts",
  ],
  coverageThreshold: {
    global: {
      branches: 65,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  setupFilesAfterEnv: ["<rootDir>/src/test/setup.ts"],
};
