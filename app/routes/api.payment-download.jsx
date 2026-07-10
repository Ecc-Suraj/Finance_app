export const loader = async () => {
  const response = await fetch("http://127.0.0.1:8000/download-payment-report");

  if (!response.ok) {
    return new Response(
      JSON.stringify({
        error: "Unable to download report",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
  }

  const blob = await response.arrayBuffer();

  return new Response(blob, {
    status: 200,
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": 'attachment; filename="payment_report.csv"',
    },
  });
};
