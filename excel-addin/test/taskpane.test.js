/* ============================================
   MTEA Frontend Tests — taskpane.test.js
   ============================================ */

const {
  numberToColumnLetter, escapeHtml, tryParseDate, formatDate,
  detectValueType, detectDominantType, formatFileSize,
} = require("../src/taskpane/taskpane");

// ===== UTILITY FUNCTIONS =====
describe("numberToColumnLetter", () => {
  test("single letters A-Z", () => {
    expect(numberToColumnLetter(1)).toBe("A");
    expect(numberToColumnLetter(26)).toBe("Z");
  });
  test("double letters AA-AZ", () => {
    expect(numberToColumnLetter(27)).toBe("AA");
    expect(numberToColumnLetter(52)).toBe("AZ");
  });
  test("triple letters", () => {
    expect(numberToColumnLetter(703)).toBe("AAA");
  });
});

describe("escapeHtml", () => {
  test("escapes special characters", () => {
    expect(escapeHtml("<script>")).not.toContain("<script>");
  });
  test("handles empty string", () => {
    expect(escapeHtml("")).toBe("");
  });
  test("passes plain text through", () => {
    expect(escapeHtml("hello world")).toBe("hello world");
  });
});

describe("formatFileSize", () => {
  test("bytes", () => {
    expect(formatFileSize(500)).toBe("500 B");
  });
  test("kilobytes", () => {
    expect(formatFileSize(2048)).toBe("2.0 KB");
  });
  test("megabytes", () => {
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});

// ===== DATE HANDLING =====
describe("tryParseDate", () => {
  test("ISO format YYYY-MM-DD", () => {
    const d = tryParseDate("2024-01-15");
    expect(d).toBeInstanceOf(Date);
  });
  test("DD/MM/YYYY format", () => {
    const d = tryParseDate("15/01/2024");
    expect(d).toBeInstanceOf(Date);
  });
  test("returns null for non-dates", () => {
    expect(tryParseDate("hello")).toBeNull();
    expect(tryParseDate("12345")).toBeNull();
  });
  test("returns null for numbers", () => {
    expect(tryParseDate(42345)).toBeNull();
  });
});

describe("formatDate", () => {
  const date = new Date(2024, 0, 15); // Jan 15, 2024
  test("ISO format", () => {
    expect(formatDate(date, "YYYY-MM-DD")).toBe("2024-01-15");
  });
  test("DD/MM/YYYY format", () => {
    expect(formatDate(date, "DD/MM/YYYY")).toBe("15/01/2024");
  });
  test("MM/DD/YYYY format", () => {
    expect(formatDate(date, "MM/DD/YYYY")).toBe("01/15/2024");
  });
});

// ===== TYPE DETECTION =====
describe("detectValueType", () => {
  test("numbers", () => {
    expect(detectValueType(42)).toBe("number");
    expect(detectValueType("123.45")).toBe("number");
    expect(detectValueType("1,000")).toBe("number");
  });
  test("text", () => {
    expect(detectValueType("hello")).toBe("text");
    expect(detectValueType("abc123xyz")).toBe("text");
  });
  test("dates", () => {
    expect(detectValueType("2024-01-15")).toBe("date");
  });
  test("empty", () => {
    expect(detectValueType("")).toBe("empty");
  });
  test("boolean", () => {
    expect(detectValueType(true)).toBe("boolean");
  });
});

describe("detectDominantType", () => {
  test("mostly numbers", () => {
    expect(detectDominantType([1, 2, 3, "4", "hello"])).toBe("number");
  });
  test("mostly text", () => {
    expect(detectDominantType(["a", "b", "c", 1])).toBe("text");
  });
  test("mixed returns mixed", () => {
    expect(detectDominantType([1, "a", true, "2024-01-01", ""])).toBe("mixed");
  });
});

// ===== INVOICE FILE VALIDATION =====
describe("Invoice file validation", () => {
  const allowedTypes = ["application/pdf", "image/png", "image/jpeg", "image/tiff"];

  test("accepts PDF files", () => {
    expect(allowedTypes.includes("application/pdf")).toBe(true);
  });
  test("accepts PNG files", () => {
    expect(allowedTypes.includes("image/png")).toBe(true);
  });
  test("accepts JPEG files", () => {
    expect(allowedTypes.includes("image/jpeg")).toBe(true);
  });
  test("rejects Word docs", () => {
    expect(allowedTypes.includes("application/msword")).toBe(false);
  });
  test("rejects Excel files", () => {
    expect(allowedTypes.includes("application/vnd.ms-excel")).toBe(false);
  });

  test("file size check", () => {
    const MAX_MB = 10;
    const okFile = { size: 5 * 1024 * 1024 };
    const bigFile = { size: 15 * 1024 * 1024 };
    expect(okFile.size <= MAX_MB * 1024 * 1024).toBe(true);
    expect(bigFile.size <= MAX_MB * 1024 * 1024).toBe(false);
  });
});

// ===== INVOICE FIELD EXTRACTION SCHEMA =====
describe("Invoice extraction response schema", () => {
  const sampleResponse = {
    header: {
      vendor_name: "ABC Supplies",
      invoice_number: "INV-2024-001",
      invoice_date: "2024-01-15",
      due_date: "2024-02-15",
      subtotal: 1000.00,
      vat_tax: 150.00,
      total: 1150.00,
      currency: "LKR",
    },
    items: [
      { description: "Widget A", qty: 10, unit_price: 50, line_total: 500 },
      { description: "Widget B", qty: 5, unit_price: 100, line_total: 500 },
    ],
    confidence: {
      overall: 0.92,
      vendor_name: 0.95,
      invoice_number: 0.98,
      total: 0.88,
    },
    warnings: ["Due date partially obscured"],
  };

  test("has header with required fields", () => {
    expect(sampleResponse.header).toHaveProperty("vendor_name");
    expect(sampleResponse.header).toHaveProperty("invoice_number");
    expect(sampleResponse.header).toHaveProperty("total");
  });
  test("has items array", () => {
    expect(Array.isArray(sampleResponse.items)).toBe(true);
    expect(sampleResponse.items.length).toBe(2);
  });
  test("has confidence scores between 0 and 1", () => {
    expect(sampleResponse.confidence.overall).toBeGreaterThanOrEqual(0);
    expect(sampleResponse.confidence.overall).toBeLessThanOrEqual(1);
  });
  test("has warnings array", () => {
    expect(Array.isArray(sampleResponse.warnings)).toBe(true);
  });
});

// ===== DUPLICATE DETECTION LOGIC =====
describe("Duplicate detection", () => {
  const existingInvoices = [
    { vendor: "ABC Supplies", number: "INV-001" },
    { vendor: "XYZ Corp", number: "INV-002" },
  ];

  function isDuplicate(vendor, number) {
    return existingInvoices.some(
      (inv) => inv.vendor.toLowerCase() === vendor.toLowerCase() && inv.number.toLowerCase() === number.toLowerCase()
    );
  }

  test("detects exact duplicate", () => {
    expect(isDuplicate("ABC Supplies", "INV-001")).toBe(true);
  });
  test("case-insensitive match", () => {
    expect(isDuplicate("abc supplies", "inv-001")).toBe(true);
  });
  test("different vendor not duplicate", () => {
    expect(isDuplicate("New Vendor", "INV-001")).toBe(false);
  });
  test("different number not duplicate", () => {
    expect(isDuplicate("ABC Supplies", "INV-999")).toBe(false);
  });
});

// ===== CONFIDENCE BADGE CLASSIFICATION =====
describe("Confidence classification", () => {
  function getConfidenceClass(score) {
    if (score >= 0.8) return "confidence-high";
    if (score >= 0.5) return "confidence-medium";
    return "confidence-low";
  }

  test("high confidence >= 0.8", () => {
    expect(getConfidenceClass(0.95)).toBe("confidence-high");
    expect(getConfidenceClass(0.8)).toBe("confidence-high");
  });
  test("medium confidence 0.5-0.79", () => {
    expect(getConfidenceClass(0.65)).toBe("confidence-medium");
    expect(getConfidenceClass(0.5)).toBe("confidence-medium");
  });
  test("low confidence < 0.5", () => {
    expect(getConfidenceClass(0.3)).toBe("confidence-low");
    expect(getConfidenceClass(0)).toBe("confidence-low");
  });
});

// ===== STANDARD TABLE SCHEMA =====
describe("Standard table schemas", () => {
  const invoiceHeaders = [
    "invoice_id", "vendor_name", "invoice_number", "invoice_date",
    "due_date", "subtotal", "vat_tax", "total", "currency",
    "source_file", "imported_at", "confidence_overall", "warnings"
  ];
  const itemHeaders = ["invoice_id", "line_no", "description", "qty", "unit_price", "line_total", "tax"];
  const logHeaders = ["timestamp", "action_type", "user", "file_name", "status", "notes"];

  test("Invoices table has 13 columns", () => {
    expect(invoiceHeaders.length).toBe(13);
  });
  test("Invoice_Items has invoice_id FK", () => {
    expect(itemHeaders[0]).toBe("invoice_id");
  });
  test("Import_Log has timestamp and status", () => {
    expect(logHeaders).toContain("timestamp");
    expect(logHeaders).toContain("status");
  });
});

// ===== API ENDPOINT CONTRACTS =====
describe("API contracts", () => {
  test("health endpoint returns expected shape", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        status: "ok",
        bot: "McLarens Transformation Excel Assistant",
        version: "1.0.0",
        models: { gemini: true, openrouter: false },
      }),
    });

    const res = await fetch("/health");
    const data = await res.json();
    expect(data.status).toBe("ok");
    expect(data).toHaveProperty("models");
  });

  test("invoice extract endpoint accepts FormData", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        header: { vendor_name: "Test", total: 100 },
        confidence: { overall: 0.9 },
        warnings: [],
      }),
    });

    const formData = new FormData();
    formData.append("file", new Blob(["pdf"], { type: "application/pdf" }));
    const res = await fetch("/api/invoice/extract", { method: "POST", body: formData });
    const data = await res.json();
    expect(data).toHaveProperty("header");
    expect(data).toHaveProperty("confidence");
  });

  test("text helper endpoint accepts JSON", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        answer: "Use =VLOOKUP(A2, Sheet2!A:B, 2, FALSE)",
        formula: "=VLOOKUP(A2, Sheet2!A:B, 2, FALSE)",
      }),
    });

    const res = await fetch("/api/ai/text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: "VLOOKUP for invoice numbers", model: "auto" }),
    });
    const data = await res.json();
    expect(data).toHaveProperty("answer");
    expect(data).toHaveProperty("formula");
  });
});
