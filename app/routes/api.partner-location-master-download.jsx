export async function loader() {
  try {
    const response = await fetch(
      "http://127.0.0.1:8000/partner-location-master-download",
    );

    if (!response.ok) {
      return Response.json(
        {
          error: "Unable to download report",
        },
        {
          status: response.status,
        },
      );
    }

    const blob = await response.blob();

    return new Response(blob, {
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition":
          'attachment; filename="partner_location_master_report.csv"',
      },
    });
  } catch (error) {
    return Response.json(
      {
        error: error.message,
      },
      {
        status: 500,
      },
    );
  }
}
