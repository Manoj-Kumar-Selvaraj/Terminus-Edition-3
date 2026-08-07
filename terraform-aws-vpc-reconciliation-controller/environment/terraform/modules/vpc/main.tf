# Incomplete starter: data default routes remain, endpoints bind every table,
# resolver opens the world, and legacy private subnet moves are absent.

variable "desired" {
  type = any
}

locals {
  subnets = { for s in var.desired.subnets : "${s.tier}-${s.az}" => s }
  nats    = { for n in var.desired.nat_gateways : n.az => n.id }
  app_keys = [for k, s in local.subnets : k if s.tier == "app"]
}

resource "aws_vpc" "this" {
  cidr_block           = var.desired.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Environment = var.desired.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "all" {
  for_each = local.subnets

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags = {
    Name = each.value.name
    Tier = each.value.tier
  }
}

resource "aws_route_table" "all" {
  for_each = local.subnets
  vpc_id   = aws_vpc.this.id
  tags = {
    Tier             = each.value.tier
    AvailabilityZone = each.value.az
    ManagedBy        = "terraform-aws-vpc-module"
  }
}

resource "aws_route" "public_default" {
  for_each = { for k, s in local.subnets : k => s if s.tier == "public" }

  route_table_id         = aws_route_table.all[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = var.desired.internet_gateway_id
}

resource "aws_route" "app_default" {
  for_each = { for k, s in local.subnets : k => s if s.tier == "app" }

  route_table_id         = aws_route_table.all[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  # Intentionally prefers first listed NAT rather than same-AZ health.
  nat_gateway_id = values(local.nats)[0]
}

resource "aws_route" "data_default" {
  for_each = { for k, s in local.subnets : k => s if s.tier == "data" }

  route_table_id         = aws_route_table.all[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = try(local.nats[each.value.az], values(local.nats)[0])
}

resource "aws_vpc_endpoint" "gateway" {
  for_each = { for ep in var.desired.gateway_endpoints : ep.service => ep }

  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.desired.region}.${each.key}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for k, _ in local.subnets : aws_route_table.all[k].id]

  tags = {
    ManagedBy   = "terraform-aws-vpc-module"
    Environment = var.desired.environment
  }
}

resource "aws_iam_role" "flow" {
  name = "${var.desired.environment}-vpc-flow-starter"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
    }]
  })
}

resource "aws_flow_log" "this" {
  vpc_id               = aws_vpc.this.id
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = var.desired.flow_log.log_group_arn
  iam_role_arn         = aws_iam_role.flow.arn
}

resource "aws_security_group" "resolver" {
  name   = "${var.desired.environment}-resolver"
  vpc_id = aws_vpc.this.id

  ingress {
    protocol    = "tcp"
    from_port   = 53
    to_port     = 53
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "udp"
    from_port   = 53
    to_port     = 53
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "private_app_route_table_ids" {
  value = [for k in local.app_keys : aws_route_table.all[k].id]
}
