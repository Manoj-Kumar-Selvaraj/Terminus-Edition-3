variable "desired" {
  type = any
}

locals {
  subnets  = { for s in var.desired.subnets : "${s.tier}-${s.az}" => s }
  nats     = { for n in var.desired.nat_gateways : n.az => n.id }
  app_keys = [for k, s in local.subnets : k if s.tier == "app"]
}

resource "aws_vpc" "this" {
  cidr_block           = var.desired.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Environment = var.desired.environment
    ManagedBy   = "terraform-aws-vpc-module"
  }
}

resource "aws_subnet" "tier" {
  for_each = local.subnets

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.cidr
  availability_zone = each.value.az
  tags = {
    Name             = each.value.name
    Tier             = each.value.tier
    AvailabilityZone = each.value.az
    Environment      = var.desired.environment
  }
}

resource "aws_route_table" "tier" {
  for_each = local.subnets
  vpc_id   = aws_vpc.this.id
  tags = {
    Tier             = each.value.tier
    AvailabilityZone = each.value.az
    ManagedBy        = "terraform-aws-vpc-module"
  }
}

resource "aws_route_table_association" "tier" {
  for_each = local.subnets

  subnet_id      = aws_subnet.tier[each.key].id
  route_table_id = aws_route_table.tier[each.key].id
}

resource "aws_route" "public_default" {
  for_each = { for k, s in local.subnets : k => s if s.tier == "public" }

  route_table_id         = aws_route_table.tier[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = var.desired.internet_gateway_id
}

resource "aws_route" "app_default" {
  for_each = { for k, s in local.subnets : k => s if s.tier == "app" }

  route_table_id         = aws_route_table.tier[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = local.nats[each.value.az]
}

resource "aws_vpc_endpoint" "gateway" {
  for_each = { for ep in var.desired.gateway_endpoints : ep.service => ep }

  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.desired.region}.${each.key}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [for k in local.app_keys : aws_route_table.tier[k].id]

  tags = {
    ManagedBy   = "terraform-aws-vpc-module"
    Environment = var.desired.environment
  }
}

resource "aws_iam_role" "flow" {
  name = "${var.desired.environment}-vpc-flow"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "vpc-flow-logs.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "flow" {
  name = "${var.desired.environment}-vpc-flow"
  role = aws_iam_role.flow.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogGroups"]
      Resource = "${var.desired.flow_log.log_group_arn}:*"
    }]
  })
}

resource "aws_flow_log" "this" {
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = var.desired.flow_log.log_group_arn
  iam_role_arn         = aws_iam_role.flow.arn
  vpc_id               = aws_vpc.this.id
}

resource "aws_security_group" "resolver" {
  name   = "${var.desired.environment}-resolver-inbound"
  vpc_id = aws_vpc.this.id

  dynamic "ingress" {
    for_each = toset(["tcp", "udp"])
    content {
      protocol    = ingress.value
      from_port   = 53
      to_port     = 53
      cidr_blocks = var.desired.resolver.allowed_cidrs
    }
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = [var.desired.vpc_cidr]
  }

  tags = {
    ManagedBy = "terraform-aws-vpc-module"
  }
}

moved {
  from = aws_subnet.private[0]
  to   = aws_subnet.tier["app-us-east-1a"]
}

moved {
  from = aws_subnet.private[1]
  to   = aws_subnet.tier["app-us-east-1b"]
}

moved {
  from = aws_subnet.private[2]
  to   = aws_subnet.tier["app-us-east-1c"]
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = [for k, s in local.subnets : aws_subnet.tier[k].id if s.tier == "public"]
}

output "private_app_subnet_ids" {
  value = [for k, s in local.subnets : aws_subnet.tier[k].id if s.tier == "app"]
}

output "isolated_data_subnet_ids" {
  value = [for k, s in local.subnets : aws_subnet.tier[k].id if s.tier == "data"]
}

output "private_app_route_table_ids" {
  value = [for k in local.app_keys : aws_route_table.tier[k].id]
}

output "isolated_data_route_table_ids" {
  value = [for k, s in local.subnets : aws_route_table.tier[k].id if s.tier == "data"]
}
