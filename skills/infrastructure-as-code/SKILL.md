---
name: infrastructure-as-code
description: Implement Infrastructure as Code using Terraform, AWS CloudFormation, or Pulumi for reproducible and version-controlled infrastructure.
---

# Infrastructure as Code Skill

## Purpose
Manage infrastructure through code for consistency, version control, and automation.

## Terraform Example

```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Subnets
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-public-${count.index}"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
}

# RDS Database
resource "aws_db_instance" "postgres" {
  identifier        = "${var.project_name}-db"
  engine            = "postgres"
  engine_version    = "14.7"
  instance_class    = "db.t3.micro"
  allocated_storage = 20

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  skip_final_snapshot     = false
}

# Variables
variable "project_name" {
  description = "Project name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Outputs
output "database_endpoint" {
  value = aws_db_instance.postgres.endpoint
}
```

## Best Practices

✅ **State Management**: Remote state (S3 + DynamoDB lock)
✅ **Modules**: Reusable infrastructure components
✅ **Variables**: Parameterize configurations
✅ **Secrets**: Never commit secrets, use secrets manager
✅ **Environments**: Separate state per environment

## Workflow

```bash
terraform init      # Initialize
terraform plan      # Preview changes
terraform apply     # Apply changes
terraform destroy   # Tear down
```

---

**Status:** Active
**Priority:** 🔴 High (DevOps essential)
**Version:** 1.0.0
