/* Commands.js — Ribbon button handlers for McLarens Excel Assistant */

Office.onReady(() => {});

/**
 * Quick Clean — runs from ribbon button without opening taskpane.
 * Trims, fixes whitespace, and converts text-numbers in the selected range.
 */
async function quickClean(event) {
  try {
    await Excel.run(async (ctx) => {
      const range = ctx.workbook.getSelectedRange();
      range.load(["values", "rowCount", "columnCount"]);
      await ctx.sync();

      const values = range.values.map((row) =>
        row.map((cell) => {
          if (cell === null || cell === undefined || cell === "") return cell;
          let str = String(cell).trim().replace(/\s+/g, " ").replace(/[\x00-\x1F\x7F]/g, "");
          const stripped = str.replace(/[,\s]/g, "");
          if (/^-?\d+(\.\d+)?$/.test(stripped) && typeof cell === "string") {
            return parseFloat(stripped);
          }
          return str;
        })
      );

      range.values = values;
      await ctx.sync();
    });
  } catch (e) {
    console.error("Quick clean error:", e);
  }
  event.completed();
}

// Register functions
Office.actions = Office.actions || {};
Office.actions.associate("quickClean", quickClean);
