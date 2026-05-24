import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");

const run = (command, args, label) => {
  console.log(label);
  const result = spawnSync(command, args, {
    cwd: root,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
};

if (!existsSync(join(root, "node_modules"))) {
  run("npm", ["install"], "Installing root dev dependencies...");
}

if (!existsSync(join(root, "frontend", "node_modules"))) {
  run("npm", ["install", "--prefix", "frontend"], "Installing frontend dependencies...");
}

if (!existsSync(join(root, "backend", ".venv"))) {
  run("npm", ["run", "setup:backend"], "Setting up backend (first run)...");
}
