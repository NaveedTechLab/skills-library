import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

export async function exportToPdf(
  elementId: string,
  filename = 'export.pdf',
  options: { margin?: number; scale?: number } = {}
): Promise<void> {
  const el = document.getElementById(elementId);
  if (!el) throw new Error(`Element #${elementId} not found in DOM`);

  const { margin = 10, scale = 2 } = options;

  // Force white background and remove shadows for clean capture
  const original = { background: el.style.background, boxShadow: el.style.boxShadow };
  el.style.background = '#ffffff';
  el.style.boxShadow  = 'none';

  // Prevent mid-section page breaks
  const sections = el.querySelectorAll<HTMLElement>('.pdf-section');
  sections.forEach(s => { s.style.pageBreakInside = 'avoid'; });

  try {
    const canvas = await html2canvas(el, {
      scale,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    });

    const imgData  = canvas.toDataURL('image/png');
    const pdf      = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageW    = pdf.internal.pageSize.getWidth();
    const pageH    = pdf.internal.pageSize.getHeight();
    const usableW  = pageW - margin * 2;
    const imgH     = (canvas.height * usableW) / canvas.width;

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
    sections.forEach(s => { s.style.pageBreakInside = ''; });
  }
}
