// Builds letterhead/VC-Letterhead-A4.docx — the everyday Word letter template.
// Brand art is embedded as an image and body text uses Arial, so the file
// renders identically on machines without the brand fonts.
// Run: node scripts/generate_letterhead_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Header, Footer,
  BorderStyle, PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo,
  PositionalTabLeader,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const INK = "0B0B0C";
const GRAY = "5C5C63";
const ORANGE = "FF4D00";
const MM = (v) => Math.round((v / 25.4) * 1440); // mm -> DXA

const wordmark = fs.readFileSync(path.join(ROOT, "assets/brand/wordmark-print.png"));
// natural size 1759x252 px; place at 58mm wide. The installed docx build
// scales transformation values by 0.1, hence the ×10 (verified via wp:extent).
const wmW = (58 / 25.4) * 96 * 10;
const wmH = (wmW * 252) / 1759;

const rightTab = () =>
  new PositionalTab({
    alignment: PositionalTabAlignment.RIGHT,
    relativeTo: PositionalTabRelativeTo.MARGIN,
    leader: PositionalTabLeader.NONE,
  });

const rule = (edge, before, after) =>
  new Paragraph({
    spacing: { before, after, line: 240 },
    border: { [edge]: { style: BorderStyle.SINGLE, size: 4, color: INK, space: 2 } },
    children: [new TextRun({ text: "", size: 2 })],
  });

const ph = (text, opts = {}) =>
  new Paragraph({
    spacing: { after: opts.after ?? 160, line: 300 },
    children: [new TextRun({ text, bold: opts.bold ?? false, size: 21, color: INK })],
  });

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Arial", size: 21, color: INK } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          margin: {
            top: MM(42), bottom: MM(34), left: MM(22), right: MM(22),
            header: MM(14), footer: MM(12),
          },
        },
      },
      headers: {
        default: new Header({
          children: [
            new Paragraph({
              spacing: { after: 0 },
              children: [
                new ImageRun({
                  type: "png",
                  data: wordmark,
                  transformation: { width: wmW, height: wmH },
                }),
                new TextRun({
                  children: [rightTab(), "LOGISTICS × MANUFACTURING — DUBAI, UAE"],
                  font: "Arial",
                  size: 13,
                  color: GRAY,
                  characterSpacing: 20,
                }),
              ],
            }),
            rule("bottom", 140, 0),
          ],
        }),
      },
      footers: {
        default: new Footer({
          children: [
            rule("top", 0, 60),
            new Paragraph({
              spacing: { after: 0 },
              children: [
                new TextRun({ text: "VC Limited", bold: true, size: 15, color: INK }),
                new TextRun({
                  children: [
                    rightTab(),
                    "1509 Citadel Tower, Business Bay, Dubai, UAE · PO Box 377310 · info@vcltd.co · vcltd.co ",
                  ],
                  size: 15,
                  color: GRAY,
                }),
                new TextRun({ text: "■", size: 15, color: ORANGE }),
              ],
            }),
          ],
        }),
      },
      children: [
        ph("[Date]"),
        ph("[Recipient name]", { after: 0 }),
        ph("[Company]", { after: 0 }),
        ph("[Address]", { after: 240 }),
        ph("Subject: [Subject line]", { bold: true, after: 240 }),
        ph("Dear [Name],"),
        ph("[Opening paragraph — state the purpose of the letter in two or three sentences.]"),
        ph("[Supporting paragraph — the detail: context, terms, dates, next steps.]"),
        ph("[Closing paragraph — the action you are asking for, and by when.]", { after: 240 }),
        ph("Yours sincerely,", { after: 480 }),
        ph("[Full name]", { bold: true, after: 0 }),
        ph("[Job title], VC Limited"),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(ROOT, "letterhead/VC-Letterhead-A4.docx");
  fs.writeFileSync(out, buf);
  console.log("wrote", out, buf.length, "bytes");
});
