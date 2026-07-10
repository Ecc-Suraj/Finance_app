/* global process */

export const action = async ({ request }) => {
  let workflow;

  try {
    const body = await request.json();
    workflow = body.workflow;
  } catch {
    return new Response(JSON.stringify({ error: "Invalid request body" }), {
      status: 400,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  if (!workflow) {
    return new Response(
      JSON.stringify({
        error: "workflow is required",
      }),
      {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
  }

  const reportMap = {
    Payment: "/payment-report",
    Refund: "/refund-report",
    Orders: "/orders-report",
    AR_report: "/ar-report",
    Partner_Master: "/partner-master-report",
    Product_Master: "/product-master-report",
  };

  const endpoint = reportMap[workflow];

  if (!endpoint) {
    return new Response(
      JSON.stringify({
        error: "Unknown report",
      }),
      {
        status: 400,
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
  }

  const response = await fetch(`${process.env.PYTHON_API}${endpoint}`);

  if (!response.ok) {
    const text = await response.text();

    return new Response(
      JSON.stringify({
        error: text,
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
  }

  return new Response(await response.arrayBuffer(), {
    status: 200,
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition":
        response.headers.get("Content-Disposition") ??
        'attachment; filename="report.csv"',
    },
  });
};
