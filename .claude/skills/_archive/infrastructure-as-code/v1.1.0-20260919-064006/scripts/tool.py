#!/usr/bin/env python3
"""
Infrastructure as Code Tool - real Terraform HCL generation + variable validation

Commands: generate-s3-bucket, generate-vpc, validate-variables, test
"""
import argparse
import re
import sys

VALID_HCL_IDENTIFIER = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")


def validate_hcl_identifier(name: str) -> bool:
    return bool(VALID_HCL_IDENTIFIER.match(name))


def generate_s3_bucket(resource_name: str, bucket_name: str, versioning=True, encrypted=True):
    if not validate_hcl_identifier(resource_name):
        raise ValueError(f"invalid Terraform resource name: {resource_name!r}")
    lines = [f'resource "aws_s3_bucket" "{resource_name}" {{', f'  bucket = "{bucket_name}"', "}"]
    if versioning:
        lines += [
            "", f'resource "aws_s3_bucket_versioning" "{resource_name}" {{',
            f'  bucket = aws_s3_bucket.{resource_name}.id',
            "  versioning_configuration {", '    status = "Enabled"', "  }", "}",
        ]
    if encrypted:
        lines += [
            "", f'resource "aws_s3_bucket_server_side_encryption_configuration" "{resource_name}" {{',
            f'  bucket = aws_s3_bucket.{resource_name}.id',
            "  rule {", "    apply_server_side_encryption_by_default {", '      sse_algorithm = "AES256"', "    }", "  }", "}",
        ]
    return "\n".join(lines) + "\n"


def generate_vpc(resource_name: str, cidr_block: str, num_public_subnets=2):
    if not validate_hcl_identifier(resource_name):
        raise ValueError(f"invalid Terraform resource name: {resource_name!r}")
    if not re.match(r"^\d+\.\d+\.\d+\.\d+/\d+$", cidr_block):
        raise ValueError(f"invalid CIDR block: {cidr_block!r}")
    lines = [
        f'resource "aws_vpc" "{resource_name}" {{', f'  cidr_block           = "{cidr_block}"',
        "  enable_dns_hostnames = true", "}", "",
        f'resource "aws_subnet" "{resource_name}_public" {{', f"  count      = {num_public_subnets}",
        f'  vpc_id     = aws_vpc.{resource_name}.id',
        f'  cidr_block = cidrsubnet(aws_vpc.{resource_name}.cidr_block, 8, count.index)', "}",
    ]
    return "\n".join(lines) + "\n"


def validate_required_variables(required, provided: dict):
    return [name for name in required if name not in provided or provided[name] in (None, "")]


# ---------------------------------------------------------------------------
# CLI ------------------------------------------------------------------
# ---------------------------------------------------------------------------

def cmd_generate_s3_bucket(args):
    try:
        print(generate_s3_bucket(args.resource_name, args.bucket_name, not args.no_versioning, not args.no_encryption))
    except ValueError as e:
        print(str(e))
        return 1
    return 0


def cmd_generate_vpc(args):
    try:
        print(generate_vpc(args.resource_name, args.cidr, args.public_subnets))
    except ValueError as e:
        print(str(e))
        return 1
    return 0


def cmd_validate_variables(args):
    import json
    provided = json.loads(args.provided)
    missing = validate_required_variables(args.required.split(","), provided)
    if not missing:
        print("OK: all required variables provided")
        return 0
    print("MISSING: " + ", ".join(missing))
    return 1


def cmd_test(args):
    hcl = generate_s3_bucket("data", "my-app-data-bucket")
    ok = 'resource "aws_s3_bucket" "data"' in hcl and "versioning_configuration" in hcl
    vpc_hcl = generate_vpc("main", "10.0.0.0/16")
    ok = ok and 'cidr_block           = "10.0.0.0/16"' in vpc_hcl
    try:
        generate_vpc("main", "not-a-cidr")
        ok = False
    except ValueError:
        pass
    missing = validate_required_variables(["region", "project_name"], {"region": "us-east-1"})
    ok = ok and missing == ["project_name"]
    print("SELF-TEST PASS" if ok else "SELF-TEST FAIL")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="Infrastructure as Code Tool")
    sub = parser.add_subparsers(dest="command")

    s3_p = sub.add_parser("generate-s3-bucket")
    s3_p.add_argument("--resource-name", required=True)
    s3_p.add_argument("--bucket-name", required=True)
    s3_p.add_argument("--no-versioning", action="store_true")
    s3_p.add_argument("--no-encryption", action="store_true")

    vpc_p = sub.add_parser("generate-vpc")
    vpc_p.add_argument("--resource-name", required=True)
    vpc_p.add_argument("--cidr", required=True)
    vpc_p.add_argument("--public-subnets", type=int, default=2)

    var_p = sub.add_parser("validate-variables")
    var_p.add_argument("--required", required=True, help="comma-separated")
    var_p.add_argument("--provided", required=True, help="JSON object")

    sub.add_parser("test")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "generate-s3-bucket": cmd_generate_s3_bucket,
        "generate-vpc": cmd_generate_vpc,
        "validate-variables": cmd_validate_variables,
        "test": cmd_test,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
