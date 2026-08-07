locals {
  slots            = toset([for i in range(var.slot_count) : tostring(i)])
  sorted_prefixes  = sort(var.endpoint_prefix_lists)
  kms_resources    = sort([for v in var.ebs_volumes : v.kms_key_arn])
  volume_defs      = { for v in var.ebs_volumes : v.logical_name => v }
  volume_pairs = {
    for pair in flatten([
      for slot in local.slots : [
        for name, def in local.volume_defs : {
          key          = "${slot}:${name}"
          slot         = slot
          logical_name = name
          size_gb      = def.size_gb
          kms_key_arn  = def.kms_key_arn
          kms_key_alias = def.kms_key_alias
        }
      ]
    ]) : pair.key => pair
  }
}

resource "aws_launch_template" "this" {
  name_prefix   = "${var.app}-${var.environment}-"
  image_id      = var.ami_id
  instance_type = var.instance_type
  user_data     = base64encode("userdata-sha256=${var.user_data_sha256}")

  metadata_options {
    http_tokens                 = "required"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 1
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Application            = var.app
      Environment            = var.environment
      CommitSha              = var.commit_sha
      BuildId                = var.build_id
      ReleaseManifestSha256  = var.manifest_sha256
      ManagedBy              = "terraform-aws-ec2-module"
    }
  }

  tags = {
    Application           = var.app
    Environment           = var.environment
    CommitSha             = var.commit_sha
    BuildId               = var.build_id
    ReleaseManifestSha256 = var.manifest_sha256
    ManagedBy             = "terraform-aws-ec2-module"
  }
}

resource "aws_autoscaling_group" "this" {
  name                      = "asg-${var.app}-${var.environment}"
  desired_capacity          = var.desired_capacity
  min_size                  = var.min_size
  max_size                  = var.max_size
  vpc_zone_identifier       = var.subnet_ids
  health_check_type         = "EC2"
  health_check_grace_period = 120
  max_instance_lifetime     = 0

  launch_template {
    id      = aws_launch_template.this.id
    version = aws_launch_template.this.latest_version
  }

  tag {
    key                 = "Application"
    value               = var.app
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "ReleaseManifestSha256"
    value               = var.manifest_sha256
    propagate_at_launch = true
  }

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = ceil((var.desired_capacity - var.max_unavailable) * 100 / var.desired_capacity)
      max_healthy_percentage = 100
      instance_warmup        = 60
    }
  }
}

resource "aws_security_group" "instance" {
  name = "${var.app}-${var.environment}-instance"

  ingress {
    protocol        = "tcp"
    from_port       = var.service_port
    to_port         = var.service_port
    security_groups = [var.alb_security_group_id]
  }

  egress {
    protocol        = "tcp"
    from_port       = 443
    to_port         = 443
    prefix_list_ids = local.sorted_prefixes
  }

  egress {
    protocol        = "udp"
    from_port       = 53
    to_port         = 53
    security_groups = [var.resolver_security_group_id]
  }

  egress {
    protocol        = "tcp"
    from_port       = 53
    to_port         = 53
    security_groups = [var.resolver_security_group_id]
  }
}

resource "aws_iam_role" "instance" {
  name = "role-${var.app}-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "instance" {
  name = "policy-${var.app}-${var.environment}"
  role = aws_iam_role.instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SsmControlPlane"
        Effect   = "Allow"
        Action   = ["ec2messages:GetMessages", "ssm:UpdateInstanceInformation", "ssmmessages:CreateControlChannel", "ssmmessages:OpenControlChannel"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "aws:ResourceAccount" = var.account_id
          }
        }
      },
      {
        Sid      = "ReadReleaseArtifact"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${trimsuffix(var.artifact_bucket_arn, "/")}/*"
      },
      {
        Sid      = "DecryptDataVolume"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = local.kms_resources
      },
      {
        Sid      = "PublishPaymentsMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = var.metric_namespace
          }
        }
      }
    ]
  })
}

resource "aws_ebs_volume" "data" {
  for_each = local.volume_pairs

  availability_zone = "us-east-1a"
  size              = each.value.size_gb
  type              = "gp3"
  encrypted         = true
  kms_key_id        = each.value.kms_key_arn

  tags = {
    Application = var.app
    Environment = var.environment
    Slot        = each.value.slot
    VolumeRole  = each.value.logical_name
    ManagedBy   = "terraform-aws-ec2-module"
  }
}

resource "aws_volume_attachment" "data" {
  for_each = aws_ebs_volume.data

  device_name = "/dev/sdf"
  volume_id   = each.value.id
  instance_id = "i-${var.app}-${each.value.tags.Slot}-planned"
}

resource "aws_cloudwatch_log_group" "rollout" {
  name              = "/rollout/${var.app}/${var.environment}"
  retention_in_days = 30
}
