# Incomplete outputs after the refactor — legacy names were dropped.
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
