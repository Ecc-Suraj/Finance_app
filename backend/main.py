from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

from payment_report import generate_payment_report
from export_ar_orders import generate_ar_report
from order_report import generate_order_report
from refund_report import generate_refund_report
from partner_master_report import generate_partner_master_report
from product_master_report import generate_product_master_report

app = FastAPI()


@app.get("/")
def home():
    return {
        "status": "Running"
    }


class ReportRequest(BaseModel):
    startDate: str | None = None
    endDate: str | None = None


# =====================================================
# PAYMENT REPORT
# =====================================================

@app.post("/payment-report")
def payment_report(request: ReportRequest):

    filename = generate_payment_report(
        start_date=request.startDate,
        end_date=request.endDate
    )

    return {
        "status": "success",
        "file": filename
    }


@app.get("/download-payment-report")
def download_payment_report():

    filename = "payment_report.csv"

    if not os.path.exists(filename):
        return {
            "error": "Report not found. Generate it first."
        }

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    )


# =====================================================
# AR REPORT
# =====================================================

@app.post("/ar-report")
def ar_report(request: ReportRequest):

    filename = generate_ar_report(
        start_date=request.startDate,
        end_date=request.endDate
    )

    return {
        "status": "success",
        "file": filename
    }


@app.get("/download-ar-report")
def download_ar_report():

    filename = "ar_aging_report.csv"

    if not os.path.exists(filename):
        return {
            "error": "Report not found. Generate it first."
        }

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    )


# =====================================================
# ORDER REPORT
# =====================================================

@app.post("/order-report")
def order_report(request: ReportRequest):

    filename = generate_order_report(
        start_date=request.startDate,
        end_date=request.endDate
    )

    return {
        "status": "success",
        "file": filename
    }


@app.get("/download-order-report")
def download_order_report():

    filename = "orders_report.csv"

    if not os.path.exists(filename):
        return {
            "error": "Report not found."
        }

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    )


# =====================================================
# REFUND REPORT
# =====================================================

@app.post("/refund-report")
def refund_report(request: ReportRequest):

    filename = generate_refund_report(
        start_date=request.startDate,
        end_date=request.endDate
    )

    return {
        "status": "success",
        "file": filename
    }


@app.get("/download-refund-report")
def download_refund_report():

    filename = "refund_report.csv"

    if not os.path.exists(filename):
        return {
            "error": "Report not found."
        }

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    )


# =====================================================
# PARTNER MASTER
# =====================================================

@app.post("/partner-master")
def partner_master():

    filename = generate_partner_master_report()

    return {
        "status": "success",
        "file": filename
    }


@app.get("/download-partner-master")
def download_partner_report():

    filename = "partner_master_report.csv"

    if not os.path.exists(filename):
        return {
            "error": "Report not found."
        }

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    )


# =====================================================
# PRODUCT MASTER
# =====================================================

from fastapi import HTTPException
import traceback

@app.post("/product-master")
def product_master():
    try:
        filename = generate_product_master_report()

        return {
            "status": "success",
            "file": filename
        }

    except Exception as e:
        traceback.print_exc()      # Prints full traceback in terminal
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download-product-master")
def download_product_master():

    filename = "product_master_report.csv"

    if not os.path.exists(filename):
        return {"error": "Report not found."}

    return FileResponse(
        path=filename,
        filename=filename,
        media_type="text/csv"
    )