import React from "react";

export default function ReportsPage() {
  const REPORT_CONFIG = {
    payment: {
      generate: "/api/payment-report",
      download: "/api/payment-download",
      filename: "payment_report.csv",
      requiresDates: true,
      successMessage: "Payment Report generated successfully.",
    },

    order_report: {
      generate: "/api/order-report",
      download: "/api/order-download",
      filename: "order_report.csv",
      requiresDates: true,
      successMessage: "Order Report generated successfully.",
    },

    ar_report: {
      generate: "/api/ar-report",
      download: "/api/ar-download",
      filename: "ar_aging_report.csv",
      requiresDates: true,
      successMessage: "AR Report generated successfully.",
    },

    refund_report: {
      generate: "/api/refund-report",
      download: "/api/refund-download",
      filename: "refund_report.csv",
      requiresDates: true,
      successMessage: "Refund Report generated successfully.",
    },

    partner_master: {
      generate: "/api/partner-master",
      download: "/api/partner-master-download",
      filename: "partner_master_report.csv",
      requiresDates: false,
      successMessage: "Partner Master generated successfully.",
    },
    partner_master_ll: {
      generate: "/api/partner-location-master",
      download: "/api/partner-location-master-download",
      filename: "partner_location_master_report.csv",
      requiresDates: false,
      successMessage: "Partner Location Master generated successfully.",
    },

    product_master: {
      generate: "/api/product-master",
      download: "/api/product-master-download",
      filename: "product_master_report.csv",
      requiresDates: false,
      successMessage: "Product Master generated successfully.",
    },
  };

  const [selectedReport, setSelectedReport] = React.useState("");

  const [isGenerating, setIsGenerating] = React.useState(false);

  const [downloadReady, setDownloadReady] = React.useState(false);

  const [statusMessage, setStatusMessage] = React.useState("");

  const [startDate, setStartDate] = React.useState("");

  const [endDate, setEndDate] = React.useState("");

  const handleGenerate = async () => {
    if (!selectedReport) {
      return;
    }

    const config = REPORT_CONFIG[selectedReport];

    if (!config) {
      alert("Invalid report selected.");
      return;
    }

    if (config.requiresDates) {
      if (!startDate || !endDate) {
        alert("Please select both Start Date and End Date.");
        return;
      }

      if (startDate > endDate) {
        alert("Start Date cannot be greater than End Date.");
        return;
      }
    }

    setDownloadReady(false);

    setStatusMessage("");

    try {
      setIsGenerating(true);

      const body = config.requiresDates
        ? {
            startDate,
            endDate,
          }
        : {};

      const response = await fetch(config.generate, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);

        throw new Error(err?.error || "Unable to generate report.");
      }

      setDownloadReady(true);

      setStatusMessage(`${config.successMessage} Click Download Report.`);
    } catch (error) {
      console.error(error);

      alert(error.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!selectedReport) {
      return;
    }

    const config = REPORT_CONFIG[selectedReport];

    if (!config) {
      alert("Invalid report selected.");
      return;
    }

    try {
      const response = await fetch(config.download);

      if (!response.ok) {
        const err = await response.json().catch(() => null);

        throw new Error(err?.error || "Unable to download report.");
      }

      const blob = await response.blob();

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");

      link.href = url;

      link.download = config.filename;

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);

      alert(error.message);
    }
  };

  const requiresDates = REPORT_CONFIG[selectedReport]?.requiresDates || false;
  return (
    <div style={{ padding: "1.5rem", maxWidth: 500 }}>
      <h1 style={{ marginBottom: "20px" }}>Finance Reports</h1>

      <div style={{ marginBottom: "20px" }}>
        <label
          htmlFor="report-select"
          style={{ display: "block", marginBottom: "5px" }}
        >
          Report Name
        </label>

        <select
          id="report-select"
          value={selectedReport}
          disabled={isGenerating}
          onChange={(e) => {
            setSelectedReport(e.target.value);

            setDownloadReady(false);

            setStatusMessage("");

            setStartDate("");

            setEndDate("");
          }}
          style={{
            width: "100%",
            padding: "8px",
          }}
        >
          <option value="">Select Report</option>

          <option value="payment">Payment Report</option>

          <option value="order_report">Order Report</option>

          <option value="ar_report">AR Report</option>

          <option value="refund_report">Refund Report</option>

          <option value="partner_master">Partner Master - Company</option>

          <option value="partner_master_ll">Partner Master- location</option>

          <option value="product_master">Product Master</option>
        </select>
      </div>

      {requiresDates && (
        <>
          <div style={{ marginBottom: "15px" }}>
            <label
              style={{
                display: "block",
                marginBottom: "5px",
              }}
            >
              Start Date
            </label>

            <input
              type="date"
              value={startDate}
              disabled={isGenerating}
              onChange={(e) => setStartDate(e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
              }}
            />
          </div>

          <div style={{ marginBottom: "20px" }}>
            <label
              style={{
                display: "block",
                marginBottom: "5px",
              }}
            >
              End Date
            </label>

            <input
              type="date"
              value={endDate}
              disabled={isGenerating}
              onChange={(e) => setEndDate(e.target.value)}
              style={{
                width: "100%",
                padding: "8px",
              }}
            />
          </div>
        </>
      )}

      <div
        style={{
          display: "flex",
          gap: "10px",
        }}
      >
        <button
          type="button"
          onClick={handleGenerate}
          disabled={!selectedReport || isGenerating}
        >
          {isGenerating ? "Generating..." : "Generate"}
        </button>

        <button
          type="button"
          onClick={handleDownload}
          disabled={!downloadReady || isGenerating}
        >
          Download Report
        </button>
      </div>

      {statusMessage && (
        <p
          style={{
            marginTop: "20px",
            color: "green",
          }}
        >
          {statusMessage}
        </p>
      )}
    </div>
  );
}
