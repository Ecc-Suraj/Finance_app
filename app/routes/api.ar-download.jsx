export const loader = async () => {
  const response = await fetch("http://127.0.0.1:8000/download-ar-report");

  if (!response.ok) {
    return new Response(
      JSON.stringify({
        error: "Unable to download AR report",
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
  }

  const file = await response.arrayBuffer();

  return new Response(file, {
    status: 200,
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": 'attachment; filename="ar_aging_report.csv"',
    },
  });
};
