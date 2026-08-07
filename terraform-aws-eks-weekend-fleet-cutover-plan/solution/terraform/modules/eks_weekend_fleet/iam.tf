resource "aws_iam_role" "cluster" {
  name = local.cluster_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EksControlPlaneAssume"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
    ]
  })

  tags = local.aws_tags
}

resource "aws_iam_role_policy_attachment" "cluster" {
  for_each = toset(local.cluster_managed_policies)

  role       = aws_iam_role.cluster.name
  policy_arn = each.value
}

resource "aws_iam_role" "node" {
  name = local.node_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EksNodeAssume"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      },
    ]
  })

  tags = local.aws_tags
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset(local.node_managed_policies)

  role       = aws_iam_role.node.name
  policy_arn = each.value
}

resource "aws_iam_instance_profile" "node" {
  name = local.node_profile_name
  role = aws_iam_role.node.name

  tags = local.aws_tags
}

resource "aws_iam_role_policy" "node_cluster_logs" {
  name = "${local.node_role_name}-cluster-logs"
  role = aws_iam_role.node.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ScopedClusterLogDelivery"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
        ]
        Resource = local.cluster_log_group_arn
      },
    ]
  })
}
