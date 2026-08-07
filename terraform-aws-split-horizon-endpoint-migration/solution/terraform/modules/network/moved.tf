moved {
  from = aws_subnet.private[0]
  to   = aws_subnet.this["private-a"]
}

moved {
  from = aws_subnet.private[1]
  to   = aws_subnet.this["private-b"]
}

moved {
  from = aws_route_table.private[0]
  to   = aws_route_table.this["private-a"]
}

moved {
  from = aws_route_table.private[1]
  to   = aws_route_table.this["private-b"]
}

moved {
  from = aws_security_group.endpoint[0]
  to   = aws_security_group.endpoint
}
