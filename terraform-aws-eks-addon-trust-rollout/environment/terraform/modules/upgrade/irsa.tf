# Additional IRSA policy definitions and role attachments for add-on trust

resource "aws_iam_role_policy_attachment" "ebs_csi_policy" {
  role       = aws_iam_role.ebs_csi.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
}

resource "aws_iam_role_policy_attachment" "lbc_policy" {
  role       = aws_iam_role.load_balancer.name
  policy_arn = "arn:aws:iam::123456789012:policy/AWSLoadBalancerControllerIAMPolicy"
}

resource "aws_iam_role_policy_attachment" "karpenter_policy" {
  role       = aws_iam_role.karpenter.name
  policy_arn = "arn:aws:iam::123456789012:policy/KarpenterControllerIAMPolicy"
}
