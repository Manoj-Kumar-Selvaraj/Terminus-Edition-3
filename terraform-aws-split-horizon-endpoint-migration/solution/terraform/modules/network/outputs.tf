output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr_block" {
  value = aws_vpc.this.cidr_block
}

output "private_subnet_ids" {
  value = [for k in local.private_subnet_keys : aws_subnet.this[k].id]
}

output "public_subnet_ids" {
  value = [for k in local.public_subnet_keys : aws_subnet.this[k].id]
}

output "private_route_table_ids" {
  value = [for k in local.private_rt_keys : aws_route_table.this[k].id]
}

output "public_route_table_ids" {
  value = [for k in local.public_rt_keys : aws_route_table.this[k].id]
}

output "gateway_vpc_endpoint_ids" {
  value = { for k, v in aws_vpc_endpoint.gateway : k => v.id }
}

output "interface_vpc_endpoint_ids" {
  value = { for k, v in aws_vpc_endpoint.interface : k => v.id }
}

output "endpoint_security_group_id" {
  value = aws_security_group.endpoint.id
}

output "endpoint_security_group_ids" {
  value = [aws_security_group.endpoint.id]
}

output "network" {
  value = {
    vpc                     = aws_vpc.this.id
    private_subnets         = [for k in local.private_subnet_keys : aws_subnet.this[k].id]
    endpoint_security_group = aws_security_group.endpoint.id
  }
}

output "endpoint_ids" {
  value = merge(
    { for k, v in aws_vpc_endpoint.gateway : k => v.id },
    { for k, v in aws_vpc_endpoint.interface : k => v.id }
  )
}
