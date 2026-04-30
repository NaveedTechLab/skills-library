# PDF Export Reference

## Table of Contents
1. [html2canvas + jsPDF (Default)](#1-html2canvas--jspdf-default)
2. [jsPDF Direct-Write Alternative](#2-jspdf-direct-write-alternative)
3. [Multi-Page Handling](#3-multi-page-handling)
4. [Print-Ready CSS Rules](#4-print-ready-css-rules)
5. [Browser Print Fallback](#5-browser-print-fallback)

---

## 1. html2canvas + jsPDF (Default)

Captures a DOM element as a canvas image and writes it into a PDF. Preserves visual styling exactly.

```ts
// lib/exportPdf.ts
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

export async function exportToPdf(
  elementId: string,
  filename = 'export.pdf',
  options: { margin?: number; scale?: number } = {}
): Promise<void> {
  const el = document.getElementById(elementId);
  if (!el) throw new Error(`Element #${elementId} not found`);

  const { margin = 10, scale = 2 } = options;

  // Temporarily force white background and remove shadows for clean capture
  const original = { background: el.style.background, boxShadow: el.style.boxShadow };
  el.style.background = '#ffffff';
  el.style.boxShadow  = 'none';

  try {
    const canvas = await html2canvas(el, {
      scale,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    });

    const imgData = canvas.toDataURL('image/png');
    const pdf     = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

    const pageW  = pdf.internal.pageSize.getWidth();
    const pageH  = pdf.internal.pageSize.getHeight();
    const usableW = pageW - margin * 2;
    const imgH   = (canvas.height * usableW) / canvas.width;

    // Split into pages if content is taller than one page
    let yOffset = 0;
    while (yOffset < imgH) {
      if (yOffset > 0) pdf.addPage();
      pdf.addImage(imgData, 'PNG', margin, margin - yOffset, usableW, imgH);
      yOffset += pageH - margin * 2;
    }

    pdf.save(filename);
  } finally {
    el.style.background = original.background;
    el.style.boxShadow  = original.boxShadow;
  }
}
```

**Requirements:**
```bash
npm install jspdf html2canvas
```

---

## 2. jsPDF Direct-Write Alternative

Use when you need programmatic control over layout (fonts, columns, exact positioning) rather than a screenshot.

```ts
import jsPDF from 'jspdf';

export function exportStructuredPdf(data: {
  title: string;
  sections: Array<{ heading: string; body: string }>;
}, filename = 'report.pdf') {
  const pdf    = new jsPDF();
  const pageW  = pdf.internal.pageSize.getWidth();
  const margin = 20;
  const usableW = pageW - margin * 2;
  let y = margin;

  // Title
  pdf.setFontSize(20);
  pdf.setFont('helvetica', 'bold');
  pdf.text(data.title, margin, y);
  y += 12;

  // Date
  pdf.setFontSize(10);
  pdf.setFont('helvetica', 'normal');
  pdf.setTextColor(120);
  pdf.text(`Generated ${new Date().toLocaleDateString()}`, margin, y);
  pdf.setTextColor(0);
  y += 10;

  // Separator
  pdf.setDrawColor(200);
  pdf.line(margin, y, pageW - margin, y);
  y += 8;

  // Sections
  for (const section of data.sections) {
    // Page break check
    if (y > pdf.internal.pageSize.getHeight() - 40) {
      pdf.addPage();
      y = margin;
    }

    pdf.setFontSize(13);
    pdf.setFont('helvetica', 'bold');
    pdf.text(section.heading, margin, y);
    y += 7;

    pdf.setFontSize(11);
    pdf.setFont('helvetica', 'normal');
    const lines = pdf.splitTextToSize(section.body, usableW);
    pdf.text(lines, margin, y);
    y += lines.length * 6 + 8;
  }

  pdf.save(filename);
}
```

---

## 3. Multi-Page Handling

The html2canvas approach in Section 1 handles multi-page via a `while` loop. Key issue: content is sliced mid-element.

**To prevent mid-element page breaks**, add `page-break-inside: avoid` to critical containers before capturing:

```ts
// Before html2canvas capture
const sections = el.querySelectorAll('.pdf-section');
sections.forEach(s => (s as HTMLElement).style.pageBreakInside = 'avoid');

const canvas = await html2canvas(el, { ... });

// Restore
sections.forEach(s => (s as HTMLElement).style.pageBreakInside = '');
```

---

## 4. Print-Ready CSS Rules

Apply these styles to the result panel element. The `print.css` asset file contains the full stylesheet.

```css
/* styles/print.css */

/* Base: always white background, no transparency */
#ai-result-panel {
  background: #ffffff !important;
  color: #000000 !important;
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 11pt;
  line-height: 1.6;
  max-width: 800px;
  margin: 0 auto;
  padding: 40px;
  box-shadow: none !important;
}

/* Headings */
#ai-result-panel h2 {
  font-size: 18pt;
  font-weight: bold;
  border-bottom: 2pt solid #000;
  padding-bottom: 6pt;
  margin-bottom: 14pt;
}

#ai-result-panel h3 {
  font-size: 13pt;
  font-weight: bold;
  margin: 16pt 0 6pt;
}

/* Lists */
#ai-result-panel ul,
#ai-result-panel ol {
  padding-left: 20pt;
  margin: 6pt 0;
}

#ai-result-panel li {
  margin-bottom: 4pt;
}

/* Priority badges — use text instead of color for print */
.priority-high   { border-left: 3pt solid #000; }
.priority-medium { border-left: 3pt solid #666; }
.priority-low    { border-left: 3pt solid #999; }

/* Page break control */
.pdf-section {
  page-break-inside: avoid;
  break-inside: avoid;
}

/* Print media query — affects browser print dialog */
@media print {
  body * { visibility: hidden; }
  #ai-result-panel,
  #ai-result-panel * { visibility: visible; }
  #ai-result-panel {
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    padding: 20mm;
  }
  .no-print { display: none !important; }
}
```

**Print-ready rules:**
- No gradients, no transparency, no shadows
- Black text on white background only
- Serif font for body text (better readability on paper)
- All colors must have sufficient contrast for B&W printing

---

## 5. Browser Print Fallback

Offer `window.print()` as a no-dependency alternative. Requires `@media print` CSS to be in place.

```tsx
<div className="no-print" style={{ display: 'flex', gap: 12, marginTop: 24 }}>
  <button onClick={() => exportToPdf('ai-result-panel', 'report.pdf')}>
    Export PDF
  </button>
  <button onClick={() => window.print()} style={{ background: 'none', border: '1px solid #d1d5db' }}>
    Print
  </button>
</div>
```

The `.no-print` class hides the button row during printing (defined in `print.css`).
