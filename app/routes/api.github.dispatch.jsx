/* global process */

export const action = async ({ request }) => {
  const body = await request.json();
  const workflow = body?.workflow;
  const startDate = body?.startDate;
  const endDate = body?.endDate;
  const start_date = body?.start_date || body?.["start-date"];
  const end_date = body?.end_date || body?.["end-date"];

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
          "Missing GitHub configuration: set GITHUB_REPO_OWNER, GITHUB_REPO_NAME, and GITHUB_TOKEN",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  const workflowMap = {
    build: "build.yml",
    deploy: "deploy.yml",
    test: "test.yml",
    all: ["build.yml", "deploy.yml", "test.yml"],
    sales: "shopify-export.yml",
    inventory: "ar-aging-export.yml",
    customers: "shopify-export.yml",
    "ar-aging-export": "ar-aging-export.yml",
    "shopify-export": "shopify-export.yml",
  };

  let target = workflowMap[workflow];

  if (!target) {
    if (workflow.endsWith(".yml") || workflow.endsWith(".yaml")) {
      target = workflow;
    } else {
      target = `${workflow}.yml`;
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
    // Some workflows (in this repo or remote) may not accept inputs and
    // GitHub will reject dispatches that include unexpected inputs (422).
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
      const text = await response.text();
      throw new Error(
        `GitHub workflow dispatch failed for ${workflowFile}: ${response.status} ${text}`,
      );
    }
  };

  try {
    const dispatchedAt = new Date().toISOString();

    if (Array.isArray(target)) {
      for (const workflowFile of target) {
        await dispatchWorkflow(workflowFile);
      }
    } else {
      await dispatchWorkflow(target);
    }

    return new Response(
      JSON.stringify({
        message: `Workflow ${workflow} dispatched`,
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
