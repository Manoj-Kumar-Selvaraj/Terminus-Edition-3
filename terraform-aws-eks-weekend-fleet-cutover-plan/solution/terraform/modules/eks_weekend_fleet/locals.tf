locals {
  aws_tags = merge(var.tags, {
    "wfleet.io/cluster" = var.cluster_name
  })

  cluster_role_name = "${var.resource_prefix}-eks-cluster"
  node_role_name    = "${var.resource_prefix}-eks-node"
  node_profile_name = "${var.resource_prefix}-eks-node"

  cluster_role_arn = "arn:aws:iam::${var.account_id}:role/${local.cluster_role_name}"
  node_role_arn    = "arn:aws:iam::${var.account_id}:role/${local.node_role_name}"

  irsa_role_names = {
    for key in keys(var.irsa_roles) : key => "${var.resource_prefix}-irsa-${key}"
  }

  irsa_role_arns = {
    for key, name in local.irsa_role_names : key => "arn:aws:iam::${var.account_id}:role/${name}"
  }

  cluster_managed_policies = [
    "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController",
  ]

  node_managed_policies = [
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
  ]

  cluster_log_group_name = "/aws/eks/${var.cluster_name}/cluster"
  cluster_log_group_arn  = "arn:aws:logs:${var.region}:${var.account_id}:log-group:${local.cluster_log_group_name}:*"

  autoscaler_discovery_tags = {
    "k8s.io/cluster-autoscaler/enabled"             = "true"
    "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
  }

  # Per-identity permission envelopes. Each envelope is split into an
  # unconditional discovery half and a mutation half that only bites on
  # resources tagged as belonging to this cluster.
  irsa_permissions = {
    "ebs-csi" = {
      discovery = [
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInstances",
        "ec2:DescribeSnapshots",
        "ec2:DescribeTags",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumesModifications",
      ]
      mutation = [
        "ec2:AttachVolume",
        "ec2:CreateSnapshot",
        "ec2:CreateTags",
        "ec2:DeleteSnapshot",
        "ec2:DeleteVolume",
        "ec2:DetachVolume",
        "ec2:ModifyVolume",
      ]
      condition_key   = "aws:ResourceTag/kubernetes.io/cluster/${var.cluster_name}"
      condition_value = "owned"
    }

    "cluster-autoscaler" = {
      discovery = [
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:DescribeAutoScalingInstances",
        "autoscaling:DescribeLaunchConfigurations",
        "autoscaling:DescribeScalingActivities",
        "autoscaling:DescribeTags",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeLaunchTemplateVersions",
        "eks:DescribeNodegroup",
      ]
      mutation = [
        "autoscaling:SetDesiredCapacity",
        "autoscaling:TerminateInstanceInAutoScalingGroup",
        "autoscaling:UpdateAutoScalingGroup",
      ]
      condition_key   = "autoscaling:ResourceTag/kubernetes.io/cluster/${var.cluster_name}"
      condition_value = "owned"
    }

    "aws-load-balancer-controller" = {
      discovery = [
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
      ]
      mutation = [
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DeleteTargetGroup",
        "elasticloadbalancing:DeregisterTargets",
        "elasticloadbalancing:ModifyListener",
        "elasticloadbalancing:ModifyTargetGroup",
        "elasticloadbalancing:RegisterTargets",
      ]
      condition_key   = "elasticloadbalancing:ResourceTag/elbv2.k8s.aws/cluster"
      condition_value = var.cluster_name
    }
  }

  # Values that are derived from the cluster itself rather than carried in the
  # inventory's set_values map.
  helm_controller_values = {
    "aws-load-balancer-controller" = {
      clusterName = var.cluster_name
      region      = var.region
      vpcId       = var.vpc_id
    }
  }

  weekend_parked_node_groups = {
    for key, group in var.node_groups : key => group if group.weekend_parked
  }

  weekend_schedules = {
    "scale-down" = {
      name                = "${var.resource_prefix}-weekend-scale-down"
      schedule_expression = var.weekend_schedule.scale_down_cron
      sizes = {
        for key, group in local.weekend_parked_node_groups : key => {
          min_size     = 0
          desired_size = 0
        }
      }
    }
    "scale-up" = {
      name                = "${var.resource_prefix}-weekend-scale-up"
      schedule_expression = var.weekend_schedule.scale_up_cron
      sizes = {
        for key, group in local.weekend_parked_node_groups : key => {
          min_size     = group.min_size
          desired_size = group.desired_size
        }
      }
    }
  }

  node_group_alarm_names = {
    for key in keys(var.node_groups) : key => "${var.resource_prefix}-${key}-node-cpu"
  }

  cluster_alarm_name = "${var.resource_prefix}-cluster-node-cpu"
}
