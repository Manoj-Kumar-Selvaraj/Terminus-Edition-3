resource "aws_vpc" "main" {
  cidr_block = "10.10.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support = true
  cluster_tag = "shared"
}

resource "aws_subnet" "public_a" {
  vpc_id = "vpc-platform"
  cidr_block = "10.10.1.0/24"
  availability_zone = "us-east-1a"
  kubernetes_role_elb = 1
  cluster_tag = "shared"
}

resource "aws_subnet" "public_b" {
  vpc_id = "vpc-platform"
  cidr_block = "10.10.2.0/24"
  availability_zone = "us-east-1b"
  kubernetes_role_elb = 1
  cluster_tag = "shared"
}

resource "aws_subnet" "private_a" {
  vpc_id = "vpc-platform"
  cidr_block = "10.10.11.0/24"
  availability_zone = "us-east-1a"
  kubernetes_role_internal_elb = 1
  cluster_tag = "shared"
}

resource "aws_subnet" "private_b" {
  vpc_id = "vpc-platform"
  cidr_block = "10.10.12.0/24"
  availability_zone = "us-east-1b"
  kubernetes_role_internal_elb = 1
  cluster_tag = "shared"
}

resource "aws_nat_gateway" "main" {
  subnet_id = "public-a"
  connectivity = "private-workers-only"
}

resource "aws_iam_role" "velero" {
  name = "platform-velero"
  service_account = "system:serviceaccount:velero:velero-server"
}

resource "aws_backup_vault" "platform" {
  name = "platform-mvp-backup-vault"
  daily_window = "03:00-04:00"
}

resource "helm_release" "efs_csi" {
  name = "aws-efs-csi-driver"
  chart = "aws-efs-csi-driver"
  version = "3.0.5"
  service_account = "efs-csi-controller-sa"
}
