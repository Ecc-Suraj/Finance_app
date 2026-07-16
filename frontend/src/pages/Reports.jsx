import { useState } from "react";
import API from "../services/api";

export default function Reports() {
  const [selectedReport, setSelectedReport] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const REPORT_ENDPOINTS = {
    payment: "/payment-report",
    order: "/order-report",
    refund: "/refund-report",
    ar: "/ar-report",
    "partner-master": "/partner-master",
    "product-master": "/product-master",
  };

  const DOWNLOAD_ENDPOINTS = {
    payment: "/download-payment-report",
    order: "/download-order-report",
    refund: "/download-refund-report",
    ar: "/download-ar-report",
    "partner-master": "/download-partner-master",
    "product-master": "/download-product-master",
  };

  const DOWNLOAD_FILENAMES = {
    payment: "payment_report.csv",
    order: "orders_report.csv",
    refund: "refund_report.csv",
    ar: "ar_aging_report.csv",
    "partner-master": "partner_master_report.csv",
    "product-master": "product_master_report.csv",
  };

  const requiresDates =
    selectedReport !== "partner-master" && selectedReport !== "product-master";

  const handleGenerate = async () => {
    if (!selectedReport) {
      alert("Please select a report.");
      return;
    }

    if (requiresDates) {
      if (!startDate || !endDate) {
        alert("Please select Start Date and End Date.");
        return;
      }

      if (startDate > endDate) {
        alert("Start Date cannot be greater than End Date.");
        return;
      }
    }

    try {
      const payload = requiresDates
        ? {
            startDate,
            endDate,
          }
        : {};

      const response = await API.post(
        REPORT_ENDPOINTS[selectedReport],
        payload,
      );

      console.log(response.data);

      alert("Report generated successfully.");
    } catch (error) {
      console.error(error);

      alert(
        error.response?.data?.detail ||
          error.message ||
          "Failed to generate report.",
      );
    }
  };

  const handleDownload = async () => {
    if (!selectedReport) {
      alert("Please select a report.");
      return;
    }

    try {
      const response = await API.get(DOWNLOAD_ENDPOINTS[selectedReport], {
        responseType: "blob",
      });

      const blob = new Blob([response.data]);

      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");

      link.href = url;

      link.download = DOWNLOAD_FILENAMES[selectedReport];

      document.body.appendChild(link);

      link.click();

      link.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);

      alert("Unable to download report.");
    }
  };

  return (
    <div className="container">
      <div className="report-card">
        <h1>FreProts</h1>

        <p className="subtitle">Financial Report Generation Portal</p>

        <div className="form-group">
          <label>Report Name</label>

          <select
            value={selectedReport}
            onChange={(e) => {
              setSelectedReport(e.target.value);
              setStartDate("");
              setEndDate("");
            }}
          >
            <option value="">Select Report</option>

            <option value="payment">Payment Report</option>

            <option value="order">Order Report</option>

            <option value="refund">Refund Report</option>

            <option value="ar">AR Report</option>

            <option value="partner-master">Partner Master</option>

            <option value="product-master">Product Master</option>
          </select>
        </div>

        {requiresDates && (
          <>
            <div className="form-group">
              <label>Start Date</label>

              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>End Date</label>

              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </>
        )}

        <div className="button-group">
          <button type="button" onClick={handleGenerate}>
            Generate Report
          </button>

          <button type="button" onClick={handleDownload}>
            Download Report
          </button>
        </div>
      </div>
    </div>
  );
}
