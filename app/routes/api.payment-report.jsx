export const action = async ({ request }) => {
  const { startDate, endDate } = await request.json();

  const response = await fetch("http://127.0.0.1:8000/payment-report", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      startDate,
      endDate,
    }),
  });

  const data = await response.json();

  return new Response(JSON.stringify(data), {
    status: response.status,
    headers: {
      "Content-Type": "application/json",
    },
  });
};
