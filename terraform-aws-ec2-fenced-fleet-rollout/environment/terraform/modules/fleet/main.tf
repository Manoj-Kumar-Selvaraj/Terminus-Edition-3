# Starter module intentionally drifts from the release contract:
# optional IMDS, open admin ingress, mutable AMI alias tags, unencrypted disks.

locals {
  slots = toset([for i in range(var.slot_count) : tostring(i)])
}

resource "aws_launch_template" "this" {
  name_prefix   = "${var.app}-${var.environment}-"
  image_id      = "ami-unstable-latest"
  instance_type = var.instance_type

  metadata_options {
    http_tokens                 = "optional"
    http_endpoint               = "enabled"
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Application = var.app
      Environment = var.environment
    }
  }
}

resource "aws_autoscaling_group" "this" {
  name                      = "asg-${var.app}-${var.environment}"
  desired_capacity          = var.desired_capacity
  min_size                  = var.min_size
  max_size                  = var.max_size
  vpc_zone_identifier       = var.subnet_ids
  health_check_type         = "EC2"
  health_check_grace_period = 60

  launch_template {
    id      = aws_launch_template.this.id
    version = "$Latest"
  }
}

resource "aws_security_group" "instance" {
  name = "sg-${var.app}-${var.environment}"

  ingress {
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
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
    Statement = [{
      Sid      = "Administrator"
      Effect   = "Allow"
      Action   = ["*"]
      Resource = "*"
    }]
  })
}

resource "aws_ebs_volume" "data" {
  for_each = local.slots

  availability_zone = "us-east-1a"
  size              = try(var.ebs_volumes[0].size_gb, 80)
  type              = "gp3"
  encrypted         = false

  tags = {
    Slot = each.key
  }
}

resource "aws_volume_attachment" "data" {
  for_each = aws_ebs_volume.data

  device_name = "/dev/sdf"
  volume_id   = each.value.id
  instance_id = "i-placeholder-${each.key}"
}

resource "aws_cloudwatch_log_group" "rollout" {
  name = "/rollout/${var.app}/${var.environment}"
}
