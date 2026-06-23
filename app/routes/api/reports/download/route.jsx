/* global process */

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  const reportType = url.searchParams.get("type");
  const checkOnly = url.searchParams.get("check") === "1";
  const since = url.searchParams.get("since");

  if (!reportType) {
    return new Response(JSON.stringify({ error: "type parameter required" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const owner = process.env.GITHUB_REPO_OWNER;
  const repo = process.env.GITHUB_REPO_NAME;
  const token = process.env.GITHUB_TOKEN;

  if (!owner || !repo || !token) {
    return new Response(
      JSON.stringify({ error: "GitHub configuration missing" }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      },
    );
  }

  const workflowFileMap = {
    sales: "shopify-export.yml",
    inventory: "ar-aging-export.yml",
    customers: "shopify-export.yml",
    "ar-aging-export": "ar-aging-export.yml",
    "shopify-export": "shopify-export.yml",
  };

  const workflowFile = workflowFileMap[reportType] || `${reportType}.yml`;

  try {
    const runsResponse = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${encodeURIComponent(
        workflowFile,
      )}/runs?status=completed&conclusion=success&per_page=10`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
        },
      },
    );

    if (!runsResponse.ok) {
      throw new Error(`Failed to fetch workflow runs: ${runsResponse.status}`);
    }

    const runsData = await runsResponse.json();
    const sinceTime = since ? new Date(since).getTime() : 0;
    const latestRun = runsData.workflow_runs?.find((run) => {
      if (!Number.isFinite(sinceTime) || sinceTime <= 0) return true;

      const runCreatedAt = new Date(run.created_at).getTime();
      return Number.isFinite(runCreatedAt) && runCreatedAt >= sinceTime;
    });

    if (!latestRun) {
      return new Response(
        JSON.stringify({ error: "Report workflow is still running" }),
        {
          status: 404,
          headers: { "Content-Type": "application/json" },
        },
      );
    }

    const artifactsResponse = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/actions/runs/${latestRun.id}/artifacts`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
        },
      },
    );

    if (!artifactsResponse.ok) {
      throw new Error(`Failed to fetch artifacts: ${artifactsResponse.status}`);
    }

    const artifactsData = await artifactsResponse.json();
    const artifact = artifactsData.artifacts?.find(
      (item) => !item.expired && item.archive_download_url,
    );

    if (!artifact) {
      return new Response(
        JSON.stringify({ error: "Download artifact is not ready yet" }),
        {
          status: 404,
          headers: { "Content-Type": "application/json" },
        },
      );
    }

    if (checkOnly) {
      return new Response(
        JSON.stringify({
          ready: true,
          artifactName: artifact.name,
          runId: latestRun.id,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      );
    }

    const downloadResponse = await fetch(artifact.archive_download_url, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
      },
    });

    if (!downloadResponse.ok) {
      throw new Error(
        `Failed to download artifact: ${downloadResponse.status}`,
      );
    }

    const buffer = await downloadResponse.arrayBuffer();
    const filename = artifact.name || "report.zip";

    return new Response(buffer, {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${filename}.zip"`,
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
