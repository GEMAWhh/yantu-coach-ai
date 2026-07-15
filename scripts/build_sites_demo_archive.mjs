import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const distRoot = path.join(repoRoot, "apps", "web", "dist");
const hostingConfig = path.join(repoRoot, ".openai", "hosting.json");
const archivePath = path.resolve(
  process.argv[2] ?? path.join(os.tmpdir(), "yantu-coach-demo-worker.tar.gz"),
);
const archiveRoot = path.join(
  os.tmpdir(),
  `yantu-sites-worker-${crypto.randomUUID().replaceAll("-", "")}`,
);

if (!fs.existsSync(path.join(distRoot, "index.html"))) {
  throw new Error("apps/web/dist is missing. Run `npm --prefix apps/web run build:demo` first.");
}
if (!fs.existsSync(hostingConfig)) {
  throw new Error(".openai/hosting.json is missing.");
}

fs.mkdirSync(path.join(archiveRoot, ".open-next", "assets"), { recursive: true });
fs.mkdirSync(path.join(archiveRoot, ".openai"), { recursive: true });
copyTree(distRoot, path.join(archiveRoot, ".open-next", "assets"));
fs.copyFileSync(hostingConfig, path.join(archiveRoot, ".openai", "hosting.json"));

writeFile(
  path.join(archiveRoot, ".open-next", "worker.js"),
  `export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    if (response.status !== 404) {
      return response;
    }
    const url = new URL(request.url);
    const indexUrl = new URL("/index.html", url.origin);
    return env.ASSETS.fetch(new Request(indexUrl, request));
  },
};
`,
);

writeFile(
  path.join(archiveRoot, "wrangler.jsonc"),
  `${JSON.stringify(
    {
      $schema: "node_modules/wrangler/config-schema.json",
      main: ".open-next/worker.js",
      name: "yantu-coach-demo",
      compatibility_date: "2026-07-15",
      assets: {
        directory: ".open-next/assets",
        binding: "ASSETS",
      },
    },
    null,
    2,
  )}
`,
);

writeFile(
  path.join(archiveRoot, "package.json"),
  `${JSON.stringify({ private: true, type: "module" }, null, 2)}
`,
);

fs.rmSync(archivePath, { force: true });
const tarResult = spawnSync("tar", ["-czf", archivePath, "-C", archiveRoot, "."], {
  stdio: "inherit",
});
if (tarResult.error) {
  throw tarResult.error;
}
if (tarResult.status !== 0) {
  throw new Error(`tar failed with exit code ${tarResult.status ?? "unknown"}`);
}

const archiveStats = fs.statSync(archivePath);
console.log(
  JSON.stringify(
    {
      archive: archivePath,
      archive_size: archiveStats.size,
      archive_root: archiveRoot,
    },
    null,
    2,
  ),
);

function writeFile(filePath, content) {
  fs.writeFileSync(filePath, content, "utf8");
}

function copyTree(source, destination) {
  fs.mkdirSync(destination, { recursive: true });
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destinationPath = path.join(destination, entry.name);
    if (entry.isDirectory()) {
      copyTree(sourcePath, destinationPath);
    } else if (entry.isFile()) {
      fs.copyFileSync(sourcePath, destinationPath);
    }
  }
}
