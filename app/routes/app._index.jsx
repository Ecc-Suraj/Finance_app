import React from "react";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export default function ReportsPage() {
  const [selectedReport, setSelectedReport] = React.useState("");
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [isDownloading, setIsDownloading] = React.useState(false);
  const [downloadReady, setDownloadReady] = React.useState(false);
  const [generatedSince, setGeneratedSince] = React.useState("");
  const [statusMessage, setStatusMessage] = React.useState("");

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

      const response = await fetch("/api/github/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow: selectedReport }),
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
      <h1 style={{ marginBottom: "1rem" }}>Finance Reports</h1>

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
          <option value="sales">Order Report</option>
          <option value="inventory">Ar report</option>
          <option value="customers">Partner Master</option>
        </select>
      </div>

      <div style={{ display: "flex", gap: "0.5rem" }}>
        <button
          type="button"
          onClick={
            generatedSince && !downloadReady ? handleCheckStatus : handleGenerate
          }
          disabled={!selectedReport || isGenerating}
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
