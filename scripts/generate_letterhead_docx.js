// Builds the Word letter templates in letterhead/ — one per group company.
// Brand art is embedded as an image and body text uses Arial, so the files
// render identically on machines without the brand fonts.
// Run: node scripts/generate_letterhead_docx.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Header, Footer,
  BorderStyle, PositionalTab, PositionalTabAlignment, PositionalTabRelativeTo,
  PositionalTabLeader, AlignmentType,
} = require("docx");

const ROOT = path.join(__dirname, "..");
const INK = "0B0B0C";
const GRAY = "5C5C63";
const ORANGE = "FF4D00";
const MM = (v) => Math.round((v / 25.4) * 1440); // mm -> DXA

// The installed docx build scales ImageRun transformation values by 0.1,
// hence the ×10 (verified via wp:extent in the output XML).
const IMG = (mm) => (mm / 25.4) * 96 * 10;

const COMPANIES = [
  {
    file: "VC-Letterhead-A4.docx",
    wordmark: "assets/brand/wordmark-print.png",
    natural: [1759, 252],
    heightMM: 8.3,
    eyebrow: "LOGISTICS × MANUFACTURING — DUBAI, UAE",
    footerName: "VC Limited",
    footerRight:
      "1509 Citadel Tower, Business Bay, Dubai, UAE · PO Box 377310 · info@vcltd.co · vcltd.co ",
    footerLine2: null,
  },
  {
    file: "Vanquish-Letterhead-A4.docx",
    wordmark: "assets/brand/wordmark-vanquish-print.png",
    natural: [2883, 252],
    heightMM: 8.3,
    eyebrow: "PENROSE DOCK — CORK, IRELAND",
    footerName: "Vanquish Capital Limited",
    footerRight: "First Floor, Penrose 2, Penrose Dock, Cork T23 YY09, Ireland ",
    footerLine2: "Registered in Ireland · Company No. [company number]",
  },
];

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

function build(c) {
  const img = fs.readFileSync(path.join(ROOT, c.wordmark));
  const h = IMG(c.heightMM);
  const w = (h * c.natural[0]) / c.natural[1];

  const footerChildren = [
    rule("top", 0, 60),
    new Paragraph({
      spacing: { after: 0 },
      children: [
        new TextRun({ text: c.footerName, bold: true, size: 15, color: INK }),
        new TextRun({ children: [rightTab(), c.footerRight], size: 15, color: GRAY }),
        new TextRun({ text: "■", size: 15, color: ORANGE }),
      ],
    }),
  ];
  if (c.footerLine2) {
    footerChildren.push(
      new Paragraph({
        spacing: { before: 40, after: 0 },
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: c.footerLine2, size: 15, color: GRAY })],
      })
    );
  }

  const doc = new Document({
    styles: {
      default: { document: { run: { font: "Arial", size: 21, color: INK } } },
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
                    data: img,
                    transformation: { width: w, height: h },
                  }),
                  new TextRun({
                    children: [rightTab(), c.eyebrow],
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
        footers: { default: new Footer({ children: footerChildren }) },
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
          ph(`[Job title], ${c.footerName}`),
        ],
      },
    ],
  });

  return Packer.toBuffer(doc).then((buf) => {
    const out = path.join(ROOT, "letterhead", c.file);
    fs.writeFileSync(out, buf);
    console.log("wrote", out, buf.length, "bytes");
  });
}

Promise.all(COMPANIES.map(build));
