
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";

export const generateWaterQualityPDF = async ({
  selectedLake,
  historicalReadings,
  uniqueStations,
  waterStatus,
  chartElement
}) => {
  const pdf = new jsPDF("p", "mm", "a4");

  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - margin * 2;

  let y = 20;

  const addPageIfNeeded = (requiredHeight = 10) => {
    if (y + requiredHeight > pageHeight - 15) {
      pdf.addPage();
      y = 20;
    }
  };

  const addHeading = (heading) => {
    addPageIfNeeded(15);

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(13);
    pdf.text(heading, margin, y);

    y += 9;
  };

  const addText = (text, size = 10) => {
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(size);

    const lines = pdf.splitTextToSize(
      String(text ?? "Not available"),
      contentWidth
    );

    const height = lines.length * 5;

    addPageIfNeeded(height);

    pdf.text(lines, margin, y);
    y += height + 2;
  };

  const formatValue = (value, unit = "") => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "Not available";
    }

    return `${value}${unit ? " " + unit : ""}`;
  };

  const formatDate = (date) => {
    if (!date) return "Date unavailable";

    const parsed = new Date(date);

    if (Number.isNaN(parsed.getTime())) {
      return "Date unavailable";
    }

    return parsed.toLocaleDateString("en-IN");
  };

  try {
    // REPORT TITLE
    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(20);
    pdf.text("AquaWatch", margin, y);

    y += 9;

    pdf.setFontSize(14);
    pdf.text("Water Quality Monitoring Report", margin, y);

    y += 8;

    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(9);

    pdf.text(
      `Generated on: ${new Date().toLocaleString("en-IN")}`,
      margin,
      y
    );

    y += 12;

    // LAKE DETAILS
    addHeading("1. Selected Lake Details");

    addText(
      `Lake / Location: ${selectedLake?.display_name || selectedLake?.lake_name}`
    );

    addText(
      `Latitude: ${selectedLake?.latitude ?? "Not available"}`
    );

    addText(
      `Longitude: ${selectedLake?.longitude ?? "Not available"}`
    );

    y += 4;

    // WATER STATUS
    addHeading("2. Indicative Water Quality Status");

    addText(`Status: ${waterStatus?.label || "Not available"}`);

    addText(
      waterStatus?.description || "No status description available."
    );

    addText(
      "This is a preliminary screening indicator based on available historical pH and dissolved oxygen readings. It is not a drinking-water safety assessment."
    );

    y += 4;

    // MONITORING STATIONS
    addHeading("3. Nearby CPCB Monitoring Stations");

    addText(`Total stations: ${uniqueStations.length}`);

    uniqueStations.forEach((station, index) => {
      addPageIfNeeded(12);

      addText(
        `${index + 1}. ${station.station || "Unknown station"}`
      );

      addText(
        `District: ${station.district || "-"} | State: ${station.state || "-"} | Distance: ${station.distance_km ?? "Not available"} km`,
        9
      );
    });

    y += 4;

    // HISTORICAL MEASUREMENTS
    addHeading("4. Historical Water Quality Measurements");

    addText(`Total historical readings: ${historicalReadings.length}`);

    historicalReadings.forEach((reading, index) => {
      addPageIfNeeded(30);

      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(9);

      pdf.text(
        `${index + 1}. ${reading.station || "Unknown station"}`,
        margin,
        y
      );

      y += 5;

      pdf.setFont("helvetica", "normal");

      const details = [
        `Date: ${formatDate(reading.measurement_date)}`,
        `pH: ${formatValue(reading.ph)}`,
        `Dissolved Oxygen: ${formatValue(reading.dissolved_oxygen, "mg/L")}`,
        `Turbidity: ${formatValue(reading.turbidity, "NTU")}`,
        `Temperature: ${formatValue(reading.temperature, "°C")}`,
        `Distance: ${formatValue(reading.distance_km, "km")}`
      ];

      details.forEach((detail) => {
        pdf.setFontSize(8);
        pdf.text(detail, margin + 3, y);
        y += 4;
      });

      y += 3;
    });

    // HISTORICAL CHARTS
    if (chartElement) {
      pdf.addPage();
      y = 20;

      addHeading("5. Historical Water Quality Charts");

      const canvas = await html2canvas(chartElement, {
        scale: 1.5,
        backgroundColor: "#ffffff",
        useCORS: true
      });

      const image = canvas.toDataURL("image/jpeg", 0.85);

      const imageHeight =
        (canvas.height * contentWidth) / canvas.width;

      const availableHeight = pageHeight - y - 15;

      if (imageHeight <= availableHeight) {
        pdf.addImage(
          image,
          "JPEG",
          margin,
          y,
          contentWidth,
          imageHeight
        );
      } else {
        // Fit the charts image onto the page
        const scale = availableHeight / imageHeight;

        pdf.addImage(
          image,
          "JPEG",
          margin,
          y,
          contentWidth * scale,
          availableHeight
        );
      }
    }

    // DATA LIMITATIONS
    pdf.addPage();
    y = 20;

    addHeading("6. Data Source and Limitations");

    addText(
      "Data source: Historical Central Pollution Control Board (CPCB) monitoring records imported into AquaWatch."
    );

    addText(
      "Nearby monitoring stations may be located on rivers or other water bodies rather than the selected lake itself."
    );

    addText(
      "Measurements are historical records and do not represent current or real-time water conditions."
    );

    addText(
      "Missing measurements are shown as Not available. No missing values have been estimated or fabricated."
    );

    addText(
      "The report does not certify that water is safe for drinking. A complete assessment requires appropriate laboratory testing and additional water-quality parameters."
    );

    // FOOTER ON ALL PAGES
    const totalPages = pdf.internal.getNumberOfPages();

    for (let page = 1; page <= totalPages; page++) {
      pdf.setPage(page);

      pdf.setFontSize(8);
      pdf.setFont("helvetica", "normal");

      pdf.text(
        "AquaWatch | Historical Water Quality Report",
        margin,
        pageHeight - 8
      );

      pdf.text(
        `Page ${page} of ${totalPages}`,
        pageWidth - margin,
        pageHeight - 8,
        { align: "right" }
      );
    }

    const filename =
      `AquaWatch_${(selectedLake?.lake_name || "Lake").replace(/[^a-z0-9]/gi, "_")}_Report.pdf`;

    pdf.save(filename);

  } catch (error) {
    console.error("PDF generation failed:", error);
    throw error;
  }
};
