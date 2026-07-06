/* global process */

export const action = async ({ request }) => {
  const contentType = request.headers.get("content-type")?.split(";")[0] || "";
  let workflow;
  let startDate;
  let endDate;
  let start_date;
  let end_date;

  try {
    if (contentType === "application/json" || contentType === "application/ld+json") {
      const body = await request.json();
      workflow = body?.workflow;
      startDate = body?.startDate;
      endDate = body?.endDate;
      start_date = body?.start_date || body?.["start-date"];
      end_date = body?.end_date || body?.["end-date"];
    } else if (
      contentType === "application/x-www-form-urlencoded" ||
      contentType === "multipart/form-data"
    ) {
      const formData = await request.formData();
      workflow = formData.get("workflow");
      startDate = formData.get("startDate");
      endDate = formData.get("endDate");
      start_date = formData.get("start_date");
      end_date = formData.get("end_date");
    } else {
      const text = await request.text();
      try {
        const body = JSON.parse(text || "{}");
        workflow = body?.workflow;
        startDate = body?.startDate;
        endDate = body?.endDate;
        start_date = body?.start_date;
        end_date = body?.end_date;
      } catch {
        const params = new URLSearchParams(text);
        workflow = params.get("workflow");
        startDate = params.get("startDate");
        endDate = params.get("endDate");
        start_date = params.get("start_date") || params.get("start-date");
        end_date = params.get("end_date") || params.get("end-date");
      }
    }
  } catch (error) {
    return new Response(JSON.stringify({ error: "Unable to parse request body." }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (typeof workflow !== "string") {
    workflow = workflow?.toString?.();
  }

  if (!workflow) {
    return new Response(JSON.stringify({ error: "workflow is required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const owner = process.env.GITHUB_REPO_OWNER;
  const repo = process.env.GITHUB_REPO_NAME;
  const token = process.env.GITHUB_TOKEN;

  if (!owner || !repo || !token) {
    return new Response(
      JSON.stringify({
        error:
          "Missing GitHub configuration. Set GITHUB_REPO_OWNER, GITHUB_REPO_NAME, and GITHUB_TOKEN.",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  const workflowMap = {
    all: ["build.yml", "deploy.yml", "test.yml"],
    build: "build.yml",
    deploy: "deploy.yml",
    test: "test.yml",
    Invoice: "shopify-export.yml",
    AR_report: "ar-aging-export.yml",
    Partners: "shopify-export.yml",
    "ar-aging-export": "ar-aging-export.yml",
    "shopify-export": "shopify-export.yml",
  };

  let workflowFiles = workflowMap[workflow];

  if (!workflowFiles) {
    if (workflow.endsWith(".yml") || workflow.endsWith(".yaml")) {
      workflowFiles = workflow;
    } else {
      workflowFiles = `${workflow}.yml`;
    }
  }

  const dispatchWorkflow = async (workflowFile) => {
    const inputs = {};
    const startDateValue = startDate || start_date;
    const endDateValue = endDate || end_date;

    if (startDateValue) {
      inputs["start-date"] = startDateValue;
      inputs.start_date = startDateValue;
      inputs.startDate = startDateValue;
    }
    if (endDateValue) {
      inputs["end-date"] = endDateValue;
      inputs.end_date = endDateValue;
      inputs.endDate = endDateValue;
    }

    const body = { ref: "main" };
    // Only include workflow_dispatch inputs for workflows that declare them.
    // Prevent sending unexpected inputs that cause GitHub to return 422.
    const workflowsWithInputs = new Set([
      "ar-aging-export.yml",
      "ar-aging-export",
      "shopify-export.yml",
      "shopify-export",
    ]);
    if (Object.keys(inputs).length && workflowsWithInputs.has(workflowFile)) {
      body.inputs = inputs;
    }

    const response = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(
        workflowFile,
      )}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      },
    );

      if (!response.ok) {
        const text = await response.text().catch(() => "");

        // If inputs were unexpected, retry once without inputs so the workflow still runs.
        if (response.status === 422 && /Unexpected inputs provided/.test(text)) {
          const fallbackBody = { ref: "main" };
          const fallbackResponse = await fetch(
            `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(
              workflowFile,
            )}/dispatches`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                Accept: "application/vnd.github+json",
                "Content-Type": "application/json",
              },
              body: JSON.stringify(fallbackBody),
            },
          );

          if (!fallbackResponse.ok) {
            const fbText = await fallbackResponse.text().catch(() => "");
            throw new Error(
              `Failed to dispatch ${workflowFile} (fallback): ${fallbackResponse.status} ${fbText}`,
            );
          }

          return;
        }

        throw new Error(
          `Failed to dispatch ${workflowFile}: ${response.status} ${text}`,
        );
      }
  };

  try {
    const dispatchedAt = new Date().toISOString();

    if (Array.isArray(workflowFiles)) {
      for (const workflowFile of workflowFiles) {
        await dispatchWorkflow(workflowFile);
      }
    } else {
      await dispatchWorkflow(workflowFiles);
    }

    return new Response(
      JSON.stringify({
        message: `Workflow ${workflow} dispatched successfully`,
        dispatchedAt,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
