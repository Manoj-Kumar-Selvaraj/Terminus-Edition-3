resource "aws_iam_role" "irsa" {
  for_each = var.irsa_roles

  name = local.irsa_role_names[each.key]

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "WeekendFleetWebIdentity"
        Effect = "Allow"
        Principal = {
          Federated = var.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${var.oidc_provider_url}:aud" = "sts.amazonaws.com"
            "${var.oidc_provider_url}:sub" = "system:serviceaccount:${each.value.namespace}:${each.value.service_account}"
          }
        }
      },
    ]
  })

  tags = local.aws_tags
}

resource "aws_iam_role_policy" "irsa" {
  for_each = var.irsa_roles

  name = "${local.irsa_role_names[each.key]}-inline"
  role = aws_iam_role.irsa[each.key].name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "Discovery"
        Effect   = "Allow"
        Action   = local.irsa_permissions[each.key].discovery
        Resource = "*"
      },
      {
        Sid      = "ScopedMutation"
        Effect   = "Allow"
        Action   = local.irsa_permissions[each.key].mutation
        Resource = "*"
        Condition = {
          StringEquals = {
            (local.irsa_permissions[each.key].condition_key) = local.irsa_permissions[each.key].condition_value
          }
        }
      },
    ]
  })
}
