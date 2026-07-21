export const action = async () => {

  const response = await fetch(
    "http://127.0.0.1:8000/partner-master",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  const data = await response.json();

  return new Response(
    JSON.stringify(data),
    {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

};