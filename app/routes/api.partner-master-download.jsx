export const loader = async () => {
  const response = await fetch("http://127.0.0.1:8000/download-partner-master");

  if (!response.ok) {
    return new Response(
      JSON.stringify({
        error: "Unable to download Partner Master Report",
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
      "Content-Disposition": 'attachment; filename="partner_master_report.csv"',
    },
  });
};
