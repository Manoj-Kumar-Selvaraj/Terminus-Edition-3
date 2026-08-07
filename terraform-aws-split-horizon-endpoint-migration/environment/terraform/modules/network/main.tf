# Intentionally broken starter after the for_each refactor.
# See /app/docs/split-horizon-contract.md and /app/evidence.

locals {
  private_subnet_keys = [for k, v in var.inventory.subnets : k if v.tier == "private"]
  public_subnet_keys  = [for k, v in var.inventory.subnets : k if v.tier == "public"]
  private_rt_keys     = [for k, v in var.inventory.route_tables : k if v.tier == "private"]
  public_rt_keys      = [for k, v in var.inventory.route_tables : k if v.tier == "public"]

  # BUG: gateway endpoints miss private-b and attach dynamodb to a public RT.
  gateway_rt_pairs = {
    "s3:private-a"         = { service = "s3", rt = "private-a" }
    "dynamodb:private-a"   = { service = "dynamodb", rt = "private-a" }
    "dynamodb:public-a"    = { service = "dynamodb", rt = "public-a" }
  }

  # BUG: ssm lands in a public subnet; ec2messages only one AZ; private DNS off for ssm.
  interface_subnet_pairs = {
    "ssm:public-b"           = { service = "ssm", subnet = "public-b" }
    "ssmmessages:private-a"  = { service = "ssmmessages", subnet = "private-a" }
    "ssmmessages:private-b"  = { service = "ssmmessages", subnet = "private-b" }
    "ec2messages:private-a"  = { service = "ec2messages", subnet = "private-a" }
  }
}

resource "aws_vpc" "this" {
  cidr_block           = var.inventory.vpc.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name        = var.inventory.vpc.name
    Environment = var.environment
  }
}

resource "aws_vpc" "foreign" {
  cidr_block           = var.dns_zones.foreign_vpc.cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = var.dns_zones.foreign_vpc.name
  }
}

resource "aws_subnet" "this" {
  for_each = var.inventory.subnets

  vpc_id            = aws_vpc.this.id
  cidr_block        = each.value.cidr_block
  availability_zone = each.value.az
  tags = {
    Name        = "${var.environment}-${each.key}"
    Tier        = each.value.tier
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags = {
    Name = "${var.environment}-igw"
  }
}

resource "aws_eip" "nat" {
  for_each = var.inventory.nat_gateways
  domain   = "vpc"
  tags = {
    Name = each.key
  }
}

resource "aws_nat_gateway" "this" {
  for_each = var.inventory.nat_gateways

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.this[each.value.az == "us-east-1a" ? "public-a" : "public-b"].id
  tags = {
    Name = each.key
  }
  depends_on = [aws_internet_gateway.this]
}

resource "aws_route_table" "this" {
  for_each = var.inventory.route_tables
  vpc_id   = aws_vpc.this.id
  tags = {
    Name        = "${var.environment}-${each.key}"
    Tier        = each.value.tier
    Environment = var.environment
  }
}

resource "aws_route_table_association" "subnet" {
  for_each = var.inventory.subnets

  # BUG: private-a associated to public-a
  subnet_id = aws_subnet.this[each.key].id
  route_table_id = aws_route_table.this[
    each.key == "private-a" ? "public-a" : each.value.route_table_key
  ].id
}

resource "aws_route" "public_default" {
  for_each = { for k, v in var.inventory.route_tables : k => v if v.tier == "public" }

  route_table_id         = aws_route_table.this[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route" "private_nat" {
  for_each = { for k, v in var.inventory.route_tables : k => v if v.tier == "private" }

  route_table_id         = aws_route_table.this[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[each.value.nat_key].id
}

resource "aws_security_group" "endpoint" {
  name        = "staging-vpce-shared"
  description = "Shared interface endpoint security group"
  vpc_id      = aws_vpc.this.id
  tags = {
    Environment = var.environment
  }
}

resource "aws_security_group" "approved" {
  for_each = toset(var.allowed_sources.security_group_ids)
  name   = "approved-${replace(each.key, "sg-", "")}"
  vpc_id = aws_vpc.this.id
  tags = {
    SourceSg = each.key
  }
}

# BUG: open world ingress
resource "aws_vpc_security_group_ingress_rule" "open" {
  security_group_id = aws_security_group.endpoint.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
  tags = {
    Name = "temp-open"
  }
}

resource "aws_vpc_endpoint" "gateway" {
  for_each = var.endpoints.gateway

  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.inventory.region}.${each.value.service}"
  vpc_endpoint_type = "Gateway"
  tags = {
    Service      = each.key
    EndpointKind = "Gateway"
    Environment  = var.environment
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = var.endpoints.interface

  vpc_id              = aws_vpc.this.id
  service_name        = "com.amazonaws.${var.inventory.region}.${each.value.service}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = each.key == "ssm" ? false : true
  security_group_ids  = [aws_security_group.endpoint.id]
  tags = {
    Service      = each.key
    EndpointKind = "Interface"
    Environment  = var.environment
  }
}

resource "aws_vpc_endpoint_route_table_association" "gateway" {
  for_each = local.gateway_rt_pairs

  vpc_endpoint_id = aws_vpc_endpoint.gateway[each.value.service].id
  route_table_id  = aws_route_table.this[each.value.rt].id
}

resource "aws_vpc_endpoint_subnet_association" "interface" {
  for_each = local.interface_subnet_pairs

  vpc_endpoint_id = aws_vpc_endpoint.interface[each.value.service].id
  subnet_id       = aws_subnet.this[each.value.subnet].id
}

resource "aws_route53_zone" "private" {
  for_each = { for z in var.dns_zones.zones : z.key => z }

  name = each.value.name
  vpc {
    vpc_id = each.value.owner_vpc_key == "shared" ? aws_vpc.this.id : aws_vpc.foreign.id
  }
  tags = {
    ZoneKey  = each.key
    OwnerVpc = each.value.owner_vpc_key
  }
}

# BUG: also associate the foreign overlapping zone into the shared VPC view.
resource "aws_route53_zone_association" "extra" {
  for_each = {
    "overlap-shadow:shared" = {
      zone = "overlap-shadow"
    }
  }

  zone_id = aws_route53_zone.private[each.value.zone].zone_id
  vpc_id  = aws_vpc.this.id
}

resource "aws_route53_record" "zone_records" {
  for_each = {
    for item in flatten([
      for z in var.dns_zones.zones : [
        for r in z.records : {
          key  = "${z.key}:${r.name}"
          zone = z.key
          name = r.name
          ip = try(
            var.endpoints.interface[r.endpoint_key].lab_ipv4,
            r.static_ipv4
          )
        }
      ]
    ]) : item.key => item
  }

  zone_id = aws_route53_zone.private[each.value.zone].zone_id
  name    = each.value.name
  type    = "A"
  ttl     = 60
  records = [each.value.ip]
}
