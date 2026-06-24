import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "/Users/admin/tescon";
const dataPath = path.join(root, "reports", "pending_uncaptured_full_export_data_20260618.json");
const outputPath = path.join(root, "reports", "Pending_Uncaptured_Full_Export_20260618.xlsx");
const previewSummaryPath = path.join(root, "reports", "pending_export_work", "summary_preview.png");
const previewPendingPath = path.join(root, "reports", "pending_export_work", "pending_preview.png");

const payload = JSON.parse(await fs.readFile(dataPath, "utf8"));
const { summary, headers, rows } = payload;

const workbook = Workbook.create();

const summarySheet = workbook.worksheets.add("Summary");
summarySheet.showGridLines = false;
summarySheet.getRange("A1:B1").values = [["Pending Uncaptured Full Export", ""]];
summarySheet.mergeCells("A1:B1");
summarySheet.getRange("A1:B1").format = {
  fill: "#1F2937",
  font: { bold: true, color: "#FFFFFF", size: 15 },
};

const summaryRows = [
  ["Generated At", summary.generated_at],
  ["Source Catalog", summary.source_catalog],
  ["Catalog Sheet", summary.catalog_sheet],
  ["Catalog Rows", summary.catalog_rows],
  ["Catalog Unique Symbols", summary.catalog_unique_symbols],
  ["Processed Symbols (R2 parts/)", summary.processed_parts_count],
  ["Processed Objects (R2 parts/)", summary.processed_objects_count],
  ["Queued Symbols (R2 raw/, not processed)", summary.queued_raw_parts_count],
  ["Raw Objects (R2 raw/)", summary.raw_objects_count],
  ["Raw Symbols Uploaded Today (UTC)", summary.raw_parts_uploaded_today_utc],
  ["Captured or Queued Unique Symbols", summary.captured_or_queued_unique_symbols],
  ["Pending Uncaptured Symbols", summary.pending_uncaptured_symbols_count],
  ["Rule", "Catalog symbols not found in R2 parts/ and not found in R2 raw/"],
  ["Symbol Matching Note", summary.symbol_matching_note],
];
summarySheet.getRangeByIndexes(2, 0, summaryRows.length, 2).values = summaryRows;
summarySheet.getRange("A3:A16").format = {
  fill: "#F3F4F6",
  font: { bold: true, color: "#111827" },
};
summarySheet.getRange("B3:B16").format = {
  font: { color: "#111827" },
  wrapText: true,
};
summarySheet.getRange("A:A").format.columnWidth = 34;
summarySheet.getRange("B:B").format.columnWidth = 72;
summarySheet.freezePanes.freezeRows(2);

const pendingSheet = workbook.worksheets.add("Pending Uncaptured");
pendingSheet.showGridLines = false;
pendingSheet.freezePanes.freezeRows(1);

pendingSheet.getRangeByIndexes(0, 0, 1, headers.length).values = [headers];
pendingSheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF" },
  wrapText: true,
};

const chunkSize = 750;
for (let start = 0; start < rows.length; start += chunkSize) {
  const chunk = rows.slice(start, start + chunkSize);
  pendingSheet.getRangeByIndexes(1 + start, 0, chunk.length, headers.length).values = chunk;
}

const usedRows = rows.length + 1;
pendingSheet.getRangeByIndexes(0, 0, usedRows, headers.length).format = {
  font: { color: "#111827", size: 10 },
  wrapText: false,
};
pendingSheet.getRangeByIndexes(0, 0, 1, headers.length).format = {
  fill: "#0F766E",
  font: { bold: true, color: "#FFFFFF", size: 10 },
  wrapText: true,
};

headers.forEach((header, index) => {
  const column = pendingSheet.getRangeByIndexes(0, index, usedRows, 1);
  const lower = String(header).toLowerCase();
  if (lower.includes("desc") || lower.includes("text") || lower.includes("status")) {
    column.format.columnWidth = lower.includes("long") ? 48 : 30;
  } else if (lower.includes("symbol") || lower.includes("location") || lower.includes("part")) {
    column.format.columnWidth = 18;
  } else {
    column.format.columnWidth = 14;
  }
});

const symbolNumberIndex = headers.indexOf("Symbol Number");
if (symbolNumberIndex >= 0) {
  const symbolColumn = pendingSheet.getRangeByIndexes(0, symbolNumberIndex, usedRows, 1);
  symbolColumn.format.numberFormat = "@";
  symbolColumn.format.columnWidth = 18;
}

pendingSheet.getRangeByIndexes(1, 0, Math.max(1, rows.length), 1).format = {
  font: { bold: true, color: "#111827" },
};

const summaryPreview = await workbook.render({
  sheetName: "Summary",
  range: "A1:B16",
  scale: 1,
  format: "png",
});
await fs.writeFile(previewSummaryPath, new Uint8Array(await summaryPreview.arrayBuffer()));

const pendingPreview = await workbook.render({
  sheetName: "Pending Uncaptured",
  range: "A1:M25",
  scale: 1,
  format: "png",
});
await fs.writeFile(previewPendingPath, new Uint8Array(await pendingPreview.arrayBuffer()));

const inspectSummary = await workbook.inspect({
  kind: "table",
  range: "Summary!A1:B16",
  include: "values",
  tableMaxRows: 20,
  tableMaxCols: 4,
});
console.log(inspectSummary.ndjson);

const inspectPending = await workbook.inspect({
  kind: "table",
  range: "Pending Uncaptured!A1:M5",
  include: "values",
  tableMaxRows: 8,
  tableMaxCols: 15,
});
console.log(inspectPending.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 50 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(`Saved ${outputPath}`);
