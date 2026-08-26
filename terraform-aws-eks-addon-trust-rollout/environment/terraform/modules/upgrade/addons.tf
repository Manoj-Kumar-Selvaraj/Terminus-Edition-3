# EKS add-on configuration and SSM parameters for controller add-ons

resource "aws_ssm_parameter" "addon_versions" {
  for_each = {
    "vpc-cni"            = "v1.18.1-eksbuild.1"
    "kube-proxy"         = "v1.29.3-eksbuild.2"
    "coredns"            = "v1.11.1-eksbuild.8"
    "aws-ebs-csi-driver" = "v1.30.0-eksbuild.1"
  }

  name  = "/eks/${local.cluster}/addons/${each.key}/target-version"
  type  = "String"
  value = each.value

  tags = {
    AddonName = each.key
  }
}
