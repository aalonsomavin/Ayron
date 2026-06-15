// Sample data for the Ayron product UI kit.
export const SOURCES = [
  { name: "Production Postgres", type: "PostgreSQL", status: "connected", rows: "4.2M", sync: "3 min ago", color: "#336791" },
  { name: "Snowflake — Analytics", type: "Snowflake", status: "connected", rows: "128M", sync: "12 min ago", color: "#29b5e8" },
  { name: "Stripe", type: "Payments API", status: "connected", rows: "892K", sync: "1 hr ago", color: "#635bff" },
  { name: "Google Analytics 4", type: "GA4", status: "syncing", rows: "2.1M", sync: "now", color: "#e8710a" },
  { name: "HubSpot CRM", type: "CRM", status: "connected", rows: "54K", sync: "6 hr ago", color: "#ff7a59" },
  { name: "Marketing S3 bucket", type: "S3 / CSV", status: "error", rows: "—", sync: "failed", color: "#d97706" },
];

export const AVAILABLE = ["BigQuery","Redshift","MySQL","MongoDB","Salesforce","Segment","Amplitude","Shopify","Airtable","Looker","Kafka","Databricks"];

export const AUTOMATIONS = [
  { name: "Daily revenue digest", desc: "Posts yesterday's revenue + top regions to #finance", schedule: "Every day · 8:00 AM", last: "Today, 8:00 AM", on: true, channel: "Slack" },
  { name: "Churn risk alert", desc: "Flags accounts with usage down >30% week-over-week", schedule: "Every Monday · 9:00 AM", last: "Jun 9, 9:00 AM", on: true, channel: "Email" },
  { name: "Anomaly watch — signups", desc: "Notifies when signups deviate 2σ from forecast", schedule: "Hourly", last: "42 min ago", on: false, channel: "Slack" },
  { name: "Weekly KPI snapshot", desc: "Exports the executive dashboard to PDF", schedule: "Every Friday · 5:00 PM", last: "Jun 13, 5:00 PM", on: true, channel: "Drive" },
];

export const REV_BARS = [42,48,45,52,60,58,67,72,69,78,84,92];
export const TREND_PTS = [28,32,30,38,42,40,48,52,49,58,64,72];
export const REGION_ROWS = [
  { r: "EMEA", v: "$486,200", d: "+18.2%", up: true, pct: 100 },
  { r: "North America", v: "$412,840", d: "+9.4%", up: true, pct: 85 },
  { r: "APAC", v: "$248,910", d: "+22.7%", up: true, pct: 51 },
  { r: "LATAM", v: "$136,970", d: "-3.1%", up: false, pct: 28 },
];

// Agent-generated artifacts (open in the right-side panel).
export const DOC_FILE   = { id: "doc1",   kind: "doc",   name: "Q2 Revenue Report",  ext: "DOCX", meta: "Document · 4 pages" };
export const SHEET_FILE = { id: "sheet1", kind: "sheet", name: "Regional Breakdown", ext: "XLSX", meta: "Spreadsheet · 1 sheet" };
export const SHEET_HEADER = ["Region", "Revenue", "Orders", "AOV", "MoM %"];
export const SHEET_ROWS = [
  ["EMEA", "486,200", "5,632", "$86.32", "+18.2%"],
  ["North America", "412,840", "4,981", "$82.88", "+9.4%"],
  ["APAC", "248,910", "2,884", "$86.31", "+22.7%"],
  ["LATAM", "136,970", "1,712", "$80.01", "-3.1%"],
  ["Total", "1,284,920", "15,209", "$84.48", "+12.4%"],
];
