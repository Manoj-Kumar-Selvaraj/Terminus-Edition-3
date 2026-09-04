# Additional IRSA policy definitions and role attachments for add-on trust.
# Attachments are visible in terraform plans and merged by the plan normalizer.

locals {
  irsa_trust_keys = {
    ebs_csi       = "ebs_csi"
    load_balancer = "load_balancer"
    karpenter     = "karpenter"
  }

  irsa_managed_policy_arns = {
    ebs_csi       = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
    load_balancer = "arn:aws:iam::${var.defaults.account_id}:policy/AWSLoadBalancerControllerIAMPolicy"
    karpenter     = "arn:aws:iam::${var.defaults.account_id}:policy/KarpenterControllerIAMPolicy"
  }
}

resource "aws_iam_role_policy_attachment" "ebs_csi_policy" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = local.irsa_managed_policy_arns.ebs_csi
}

resource "aws_iam_role_policy_attachment" "lbc_policy" {
  role       = aws_iam_role.load_balancer.name
  policy_arn = local.irsa_managed_policy_arns.load_balancer
}

resource "aws_iam_role_policy_attachment" "karpenter_policy" {
  role       = aws_iam_role.karpenter.name
  policy_arn = local.irsa_managed_policy_arns.karpenter
}

resource "aws_iam_role_policy" "ebs_csi_describe_guard" {
  name = "ebs-csi-describe-guard"
  role = aws_iam_role.ebs_csi.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DescribeOnly"
      Effect   = "Allow"
      Action   = ["ec2:DescribeVolumes", "ec2:DescribeSnapshots"]
      Resource = "*"
    }]
  })
}

resource "aws_ssm_parameter" "irsa_subject_inventory" {
  for_each = var.trust_observations.required_subjects

  name  = "/eks/${local.cluster}/irsa/${each.key}/required-subject"
  type  = "String"
  value = each.value

  tags = {
    AddonTrust = each.key
    Component  = "irsa-subject"
  }
}

resource "aws_ssm_parameter" "irsa_role_name_inventory" {
  for_each = var.trust_observations.role_names

  name  = "/eks/${local.cluster}/irsa/${each.key}/role-name"
  type  = "String"
  value = each.value

  tags = {
    AddonTrust = each.key
    RoleName   = each.value
    Component  = "irsa-role-name"
  }
}

resource "aws_ssm_parameter" "irsa_forbidden_subjects" {
  name = "/eks/${local.cluster}/irsa/forbidden-subjects"
  type = "String"
  value = jsonencode({
    forbidden = try(var.trust_observations.forbidden_subjects, [])
  })

  tags = {
    Component = "irsa-forbidden"
  }
}
