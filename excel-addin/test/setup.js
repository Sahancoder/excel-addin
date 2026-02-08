/* Test setup — Mock Office.js, Excel.run, DOM, and fetch */

// Mock localStorage
const store = {};
global.localStorage = {
  getItem: (key) => store[key] || null,
  setItem: (key, val) => { store[key] = String(val); },
  removeItem: (key) => { delete store[key]; },
  clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
};

// Mock Office.js
global.Office = {
  HostType: { Excel: "Excel" },
  onReady: (cb) => cb({ host: "Excel", platform: "PC" }),
  actions: { associate: jest.fn() },
};

// Mock Excel.run
global.Excel = {
  run: jest.fn(async (callback) => {
    const mockRange = {
      address: "Sheet1!A1:D10",
      values: [
        ["Name", "Amount", "Date", "Status"],
        ["Alice", "1000", "2024-01-15", "Active"],
        ["Bob", "2500", "2024-02-20", "Active"],
        ["Alice", "1000", "2024-01-15", "Active"],
        ["", "", "", ""],
      ],
      rowCount: 5,
      columnCount: 4,
      numberFormat: [["General", "General", "General", "General"]],
      load: jest.fn(),
      getRow: jest.fn(() => ({
        format: { fill: { color: "" }, font: { color: "" } },
      })),
      getCell: jest.fn(() => ({
        format: {
          fill: { color: "" },
          font: { color: "" },
          borders: { getItem: jest.fn(() => ({ style: "", color: "" })) },
        },
      })),
      format: {
        fill: { color: "" },
        font: { bold: false, color: "", size: 13 },
        autofitColumns: jest.fn(),
        autofitRows: jest.fn(),
        rowHeight: 20,
        horizontalAlignment: "General",
      },
      clear: jest.fn(),
      formulas: null,
    };

    const mockSheet = {
      name: "Sheet1",
      load: jest.fn(),
      getRange: jest.fn(() => mockRange),
      getUsedRange: jest.fn(() => mockRange),
      activate: jest.fn(),
      freezePanes: { freezeRows: jest.fn() },
      getCell: jest.fn(() => mockRange),
    };

    const mockWorkbook = {
      worksheets: {
        getActiveWorksheet: jest.fn(() => mockSheet),
        getItem: jest.fn(() => mockSheet),
        add: jest.fn(() => mockSheet),
      },
      getSelectedRange: jest.fn(() => mockRange),
    };

    const ctx = {
      workbook: mockWorkbook,
      sync: jest.fn(async () => {}),
    };

    return callback(ctx);
  }),
};

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ status: "ok", version: "1.0.0" }),
  })
);

// Mock confirm
global.confirm = jest.fn(() => true);

// Mock DOM elements
const elements = {
  "connection-status": { className: "", title: "" },
  "status-banner": { className: "banner hidden", classList: { add: jest.fn(), remove: jest.fn() } },
  "banner-message": { textContent: "" },
  "banner-icon": { textContent: "" },
  "loading-overlay": { classList: { add: jest.fn(), remove: jest.fn() } },
  "loading-text": { textContent: "" },
  "model-selector": { value: "auto" },
  "invoice-dropzone": { classList: { add: jest.fn(), remove: jest.fn() }, addEventListener: jest.fn() },
  "invoice-file-input": { click: jest.fn(), value: "" },
  "invoice-progress": { classList: { add: jest.fn(), remove: jest.fn() } },
  "invoice-progress-fill": { style: { width: "0%" } },
  "invoice-progress-text": { textContent: "" },
  "invoice-review": { classList: { add: jest.fn(), remove: jest.fn() } },
  "invoice-fields": { innerHTML: "" },
  "invoice-warnings": { innerHTML: "", classList: { add: jest.fn(), remove: jest.fn() } },
  "confidence-badge": { textContent: "", className: "" },
  "clean-trim": { checked: true },
  "clean-whitespace": { checked: true },
  "clean-numbers": { checked: true },
  "clean-dates": { checked: false },
  "clean-empty": { checked: false },
  "clean-currency": { checked: false },
  "date-format": { value: "YYYY-MM-DD" },
  "clean-result": { textContent: "", className: "result-box hidden", classList: { remove: jest.fn() } },
  "val-duplicates": { checked: true },
  "val-missing": { checked: true },
  "val-types": { checked: true },
  "val-outliers": { checked: false },
  "dup-key-col": { value: "" },
  "validate-result": { textContent: "", className: "", classList: { remove: jest.fn() } },
  "ai-prompt": { value: "" },
  "ai-include-context": { checked: true },
  "ai-result": { classList: { add: jest.fn(), remove: jest.fn() } },
  "ai-answer": { textContent: "" },
  "ai-formula": { classList: { add: jest.fn(), remove: jest.fn() } },
  "ai-formula-text": { textContent: "" },
  "history-list": { innerHTML: "" },
  "setting-backend-url": { value: "https://localhost:8000" },
  "setting-max-file-size": { value: "10" },
  "setting-date-format": { value: "YYYY-MM-DD" },
  "setting-currency": { value: "LKR" },
};

document.getElementById = jest.fn((id) => elements[id] || { classList: { add: jest.fn(), remove: jest.fn() }, textContent: "", innerHTML: "", value: "" });
document.querySelectorAll = jest.fn(() => []);
document.createElement = jest.fn((tag) => ({
  textContent: "",
  innerHTML: "",
  get innerText() { return this.textContent; },
}));
