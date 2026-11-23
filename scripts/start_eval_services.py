"""Start the local retrieval/model services using the sibling Brainwave checkout."""

import argparse
import json
import subprocess
from pathlib import Path

PROJECT = "brainwave-eval-local"
INFRA = ["postgres", "mongodb", "minio", "kafka", "ollama"]
INIT = ["minio-init", "kafka-init"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--brainwave", type=Path, default=Path(__file__).resolve().parents[2] / "brainwave"
    )
    args = parser.parse_args()
    infra = args.brainwave.resolve() / "infra"
    reference = ["docker", "compose", "--env-file", "env/.env.dev", "--profile", "services"]
    for name in ("compose.yml", "compose.dev.yml", "compose.evals.yml"):
        reference.extend(["-f", f"docker/{name}"])
    source = json.loads(
        subprocess.check_output([*reference, "config", "--format", "json"], cwd=infra)
    )
    services = {name: source["services"][name] for name in [*INFRA, *INIT, "know-hub"]}
    volumes = {}
    for service in services.values():
        for key in ("profiles", "container_name", "ports", "depends_on", "networks"):
            service.pop(key, None)
        service["restart"] = "no"
        for mount in service.get("volumes", []):
            if mount["type"] == "volume":
                volumes[mount["source"]] = {}
            else:
                mount["read_only"] = True

    # Reuse installed model weights, but isolate every writable evaluation database.
    for key in ("ollama-data", "know-hub-node-modules"):
        cache = source["volumes"][key]["name"]
        if subprocess.run(["docker", "volume", "inspect", cache], capture_output=True).returncode:
            raise SystemExit(
                f"Missing Brainwave cache {cache}. Initialize the reference Eval Lab first."
            )
        volumes[key] = {"external": True, "name": cache}
    for name in ("ollama", "know-hub"):
        for mount in services[name]["volumes"]:
            mount["read_only"] = True
    services["know-hub"]["image"] = "ghcr.io/brainwave-project/brainwave-know-hub:latest"
    services["know-hub"]["environment"]["PRISMA_QUERY_ENGINE_LIBRARY"] = (
        "/workspace/know-hub/node_modules/.prisma/client/"
        "libquery_engine-linux-musl-openssl-3.0.x.so.node"
    )
    services["know-hub"]["command"] = ["./node_modules/.bin/tsx", "src/index.ts"]
    services["know-hub"]["ports"] = ["127.0.0.1:3002:3002", "127.0.0.1:50052:50052"]
    services["ollama"]["ports"] = ["127.0.0.1:11434:11434"]
    for mount in services["postgres"]["volumes"]:
        if mount["target"] == "/docker-entrypoint-initdb.d":
            mount["target"] = "/eval-ddl"
    spec = json.dumps({"services": services, "volumes": volumes}).replace("$", "$$")

    def compose(*command):
        subprocess.run(
            ["docker", "compose", "-p", PROJECT, "-f", "-", *command],
            input=spec,
            text=True,
            cwd=infra,
            check=True,
        )

    compose("up", "-d", "--wait", "--wait-timeout", "180", *INFRA)
    compose(
        "exec",
        "-T",
        "postgres",
        "sh",
        "-ec",
        """
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
SELECT to_regclass('sem.document_chunks') IS NULL AS initialize \\gset
\\if :initialize
BEGIN;
CREATE SCHEMA IF NOT EXISTS doc;
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='knowhub_app') THEN
    CREATE ROLE knowhub_app;
  END IF;
END $$;
\\i /eval-ddl/00-extensions.sql
\\i /eval-ddl/03-knowhub.sql
RESET search_path;
\\i /eval-ddl/05-semantic.sql
\\i /eval-ddl/41-doc-agent-columns.sql
COMMIT;
\\endif
SQL
    """,
    )
    for name in INIT:
        compose("run", "--rm", name)
    compose("up", "-d", "know-hub")


if __name__ == "__main__":
    main()
