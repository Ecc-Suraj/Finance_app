import React from "react";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function ReportsPage() {
  const [selectedReport, setSelectedReport] = React.useState("");
  const [startDate, setStartDate] = React.useState("");
  const [endDate, setEndDate] = React.useState("");
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [isDownloading, setIsDownloading] = React.useState(false);
  const [downloadReady, setDownloadReady] = React.useState(false);
  const [generatedSince, setGeneratedSince] = React.useState("");
  const [statusMessage, setStatusMessage] = React.useState("");

  const dateRangeReports = [
    "AR_report",
    "Invoice",
    "Refund",
    "Payment",
  ];

  const isDateRangeIncomplete =
    dateRangeReports.includes(selectedReport) &&
    ((startDate && !endDate) || (!startDate && endDate));

  const isDateRangeInvalid =
    dateRangeReports.includes(selectedReport) &&
    startDate &&
    endDate &&
    startDate > endDate;

  const checkReportReady = async (reportType, since) => {
    const readyUrl = `/api/reports/download?type=${encodeURIComponent(
      reportType,
    )}&since=${encodeURIComponent(since)}&check=1&poll=${Date.now()}`;
    const response = await fetch(readyUrl, { method: "GET", cache: "no-store" });

    if (response.ok) {
      return { ok: true };
    }

    const err = await response.json().catch(() => null);
    return { ok: false, error: err?.error || err?.message };
  };

  const waitForReportReady = async (reportType, since) => {
    const maxAttempts = 60;
    const delayMs = 5000;
    let lastError;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const ready = await checkReportReady(reportType, since);

      if (ready.ok) {
        setDownloadReady(true);
        setStatusMessage("Report generated. You can now download it.");
        return true;
      }

      lastError = ready.error;
      if (attempt % 6 === 0 && lastError) {
        setStatusMessage(`Report is generating. Last check: ${lastError}`);
      }
      await sleep(delayMs);
    }

    setStatusMessage(
      lastError ||
        "Still waiting for the download link. Please check status again in a moment.",
    );
    return false;
  };

  const handleGenerate = async () => {
    if (!selectedReport) return;

    try {
      setIsGenerating(true);
      setDownloadReady(false);
      setGeneratedSince("");
      setStatusMessage("Starting report generation...");

      if (isDateRangeInvalid) {
        throw new Error("Start date must be on or before end date.");
      }

      const payload = { workflow: selectedReport };
      if (dateRangeReports.includes(selectedReport)) {
        if (startDate) {
          payload.startDate = startDate;
          payload.start_date = startDate;
          payload["start-date"] = startDate;
        }
        if (endDate) {
          payload.endDate = endDate;
          payload.end_date = endDate;
          payload["end-date"] = endDate;
        }
      }
      console.log("Dispatch payload:", payload);
      const response = await fetch("/api/github/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        throw new Error(err?.error || "Failed to dispatch GitHub workflow");
      }

      const data = await response.json().catch(() => ({}));
      const since = data.dispatchedAt || new Date().toISOString();
      setGeneratedSince(since);
      setStatusMessage("Report is generating. Waiting for the download link...");
      await waitForReportReady(selectedReport, since);
    } catch (error) {
      console.error(error);
      setStatusMessage("");
      alert(error.message || "There was an error dispatching the workflow.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCheckStatus = async () => {
    if (!selectedReport || !generatedSince) return;

    try {
      setIsGenerating(true);
      setStatusMessage("Checking for the download link...");
      await waitForReportReady(selectedReport, generatedSince);
    } catch (error) {
      console.error(error);
      alert(error.message || "There was an error checking the report status.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = async () => {
    if (!selectedReport || !downloadReady) return;

    const downloadUrl = `/api/reports/download?type=${encodeURIComponent(
      selectedReport,
    )}&since=${encodeURIComponent(generatedSince)}`;

    try {
      setIsDownloading(true);
      const response = await fetch(downloadUrl, {
        method: "GET",
        cache: "no-store",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => null);
        throw new Error(
          err?.error ||
            err?.message ||
            "Report is not ready yet. Please try again in a minute.",
        );
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      link.download = `${selectedReport}-report.${getFileExtensionFromResponse(
        response,
      )}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      alert(error.message || "There was an error downloading the report.");
    } finally {
      setIsDownloading(false);
    }
  };

  function getFileExtensionFromResponse(response) {
    const contentType = response.headers.get("Content-Type") || "";
    if (contentType.includes("csv")) return "csv";
    if (contentType.includes("pdf")) return "pdf";
    if (contentType.includes("json")) return "json";
    if (contentType.includes("zip")) return "zip";
    return "dat";
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 480 }}>
      <h1 style={{ marginBottom: "1rem" }}>Generate Reports</h1>

      <div style={{ marginBottom: "1rem" }}>
        <label htmlFor="report-select" style={{ display: "block" }}>
          Report name
        </label>
        <select
          id="report-select"
          style={{ marginTop: "0.5rem", width: "100%", padding: "0.25rem" }}
          value={selectedReport}
          onChange={(e) => {
            setSelectedReport(e.target.value);
            setDownloadReady(false);
            setGeneratedSince("");
            setStatusMessage("");
          }}
        >
          <option value="">Select a report</option>
          <option value="Invoice">Order Report</option>
          <option value="AR_report">Ar report</option>
          <option value="Refund">Refund report</option>
          <option value="Products">Product Master</option>
          <option value="Payment">Payment report</option>
          <option value="Partners">Partner Master</option>
        </select>
      </div>

      {dateRangeReports.includes(selectedReport) && (
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="start-date" style={{ display: "block" }}>
            Start date
          </label>
          <input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setDownloadReady(false);
              setGeneratedSince("");
              setStatusMessage("");
            }}
            style={{ marginTop: "0.5rem", width: "100%", padding: "0.25rem" }}
          />

          <label
            htmlFor="end-date"
            style={{ display: "block", marginTop: "1rem" }}
          >
            End date
          </label>
          <input
            id="end-date"
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setDownloadReady(false);
              setGeneratedSince("");
              setStatusMessage("");
            }}
            style={{ marginTop: "0.5rem", width: "100%", padding: "0.25rem" }}
          />
          {isDateRangeInvalid && (
            <p style={{ marginTop: "0.5rem", color: "#b91c1c" }}>
              Start date must be on or before end date.
            </p>
          )}
          {isDateRangeIncomplete && (
            <p style={{ marginTop: "0.5rem", color: "#b91c1c" }}>
              Please enter both start and end date, or leave both blank.
            </p>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          type="button"
          onClick={
            generatedSince && !downloadReady
              ? handleCheckStatus
              : handleGenerate
          }
          disabled={
            !selectedReport ||
            isGenerating ||
            (dateRangeReports.includes(selectedReport) && isDateRangeIncomplete)
          }
        >
          {isGenerating
            ? "Generating..."
            : generatedSince && !downloadReady
              ? "Check status"
              : "Generate"}
        </button>

        <button
          type="button"
          onClick={handleDownload}
          disabled={!selectedReport || !downloadReady || isDownloading}
        >
          {isDownloading ? "Downloading..." : "Download report"}
        </button>
      </div>

      {statusMessage && <p style={{ marginTop: "1rem" }}>{statusMessage}</p>}
    </div>
  );
}
