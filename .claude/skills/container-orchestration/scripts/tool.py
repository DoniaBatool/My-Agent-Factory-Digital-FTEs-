#!/usr/bin/env python3
"""
Container Orchestration Tool - real k8s Deployment manifest generation + validation

Commands: generate-deployment, validate-resources, test
"""
import argparse
import json
import re
import sys

K8S_QUANTITY_RE = re.compile(r"^\d+(\.\d+)?(m|Mi|Gi|Ki|G|M|K)?$")


def validate_k8s_quantity(value: str) -> bool:
    return bool(K8S_QUANTITY_RE.match(value))


def build_deployment_manifest(name, image, replicas=3, port=8000, cpu_request="250m", cpu_limit="500m", mem_request="256Mi", mem_limit="512Mi", health_path="/health"):
    for label, val in [("cpu_request", cpu_request), ("cpu_limit", cpu_limit), ("mem_request", mem_request), ("mem_limit", mem_limit)]:
        if not validate_k8s_quantity(val):
            raise ValueError(f"invalid k8s resource quantity for {label}: {val!r}")

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": name, "labels": {"app": name}},
        "spec": {
            "replicas": replicas,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name}},
                "spec": {
                    "containers": [{
                        "name": name,
                        "image": image,
                        "ports": [{"containerPort": port}],
                        "resources": {
                            "requests": {"cpu": cpu_request, "memory": mem_request},
                            "limits": {"cpu": cpu_limit, "memory": mem_limit},
                        },
                        "livenessProbe": {"httpGet": {"path": health_path, "port": port}, "initialDelaySeconds": 5},
                        "readinessProbe": {"httpGet": {"path": health_path, "port": port}, "initialDelaySeconds": 2},
                    }],
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_generate_deployment(args):
    try:
        manifest = build_deployment_manifest(
            args.name, args.image, args.replicas, args.port,
            args.cpu_request, args.cpu_limit, args.mem_request, args.mem_limit, args.health_path,
        )
    except ValueError as e:
        print(str(e))
        return 1
    print(json.dumps(manifest, indent=2))
    return 0


def cmd_validate_resources(args):
    ok = validate_k8s_quantity(args.value)
    print("OK" if ok else f"INVALID: {args.value!r} is not a valid k8s resource quantity")
    return 0 if ok else 1


def cmd_test(args):
    ok = validate_k8s_quantity("250m") and validate_k8s_quantity("512Mi") and not validate_k8s_quantity("lots")
    manifest = build_deployment_manifest("todo-api", "todo-api:1.0.0", replicas=3, port=8000)
    container = manifest["spec"]["template"]["spec"]["containers"][0]
    ok = ok and container["livenessProbe"]["httpGet"]["path"] == "/health"
    ok = ok and manifest["spec"]["replicas"] == 3
    try:
        build_deployment_manifest("x", "y", cpu_request="not-a-quantity")
        ok = False
    except ValueError:
        pass
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Container Orchestration Tool")
    sub = parser.add_subparsers(dest="command")

    dep_p = sub.add_parser("generate-deployment")
    dep_p.add_argument("--name", required=True)
    dep_p.add_argument("--image", required=True)
    dep_p.add_argument("--replicas", type=int, default=3)
    dep_p.add_argument("--port", type=int, default=8000)
    dep_p.add_argument("--cpu-request", default="250m")
    dep_p.add_argument("--cpu-limit", default="500m")
    dep_p.add_argument("--mem-request", default="256Mi")
    dep_p.add_argument("--mem-limit", default="512Mi")
    dep_p.add_argument("--health-path", default="/health")

    val_p = sub.add_parser("validate-resources")
    val_p.add_argument("value")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "generate-deployment": cmd_generate_deployment,
        "validate-resources": cmd_validate_resources,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
