module.exports = {
  testEnvironment: "jsdom",
  setupFiles: ["./test/setup.js"],
  transform: {
    "^.+\\.js$": "babel-jest",
  },
  transformIgnorePatterns: ["/node_modules/"],
  moduleFileExtensions: ["js"],
  testMatch: ["**/test/**/*.test.js"],
};
