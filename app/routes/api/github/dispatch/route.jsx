/* global process */

export const action = async ({ request }) => {
  const contentType = request.headers.get("content-type")?.split(";")[0] || "";
  let workflow;

  try {
    if (contentType === "application/json" || contentType === "application/ld+json") {
      const body = await request.json();
      workflow = body?.workflow;
    } else if (
      contentType === "application/x-www-form-urlencoded" ||
      contentType === "multipart/form-data"
    ) {
      const formData = await request.formData();
      workflow = formData.get("workflow");
    } else {
      const text = await request.text();
      try {
        const body = JSON.parse(text || "{}");
        workflow = body?.workflow;
      } catch {
        const params = new URLSearchParams(text);
        workflow = params.get("workflow");
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
    sales: "shopify-export.yml",
    inventory: "ar-aging-export.yml",
    customers: "shopify-export.yml",
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
        body: JSON.stringify({ ref: "main" }),
      },
    );

    if (!response.ok) {
      const text = await response.text();
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
